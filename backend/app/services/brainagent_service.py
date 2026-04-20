"""BrainAgent — diagnóstico, exercícios, chat e recomendações via LLM (Ollama Cloud ou Anthropic)."""

from __future__ import annotations

import json
import logging
import re
import uuid
from typing import Any

from app.config import get_settings
from app.prompts.academy_teacher import ACADEMY_TEACHER_CONTEXT_BASE, ACADEMY_TEACHER_IDENTITY_EN
from app.services.llm_client import llm_complete

logger = logging.getLogger(__name__)


def diagnostic_opening_message() -> str:
    return (
        "Olá. Sou o BrainAgent da MasterAI Academy. "
        "Vou fazer perguntas em texto livre para calibrar seu nível — "
        "responda como preferir, sem medo de errar. "
        "Primeira pergunta (bloco Alfabetização): "
        "em uma frase, o que é uma métrica de negócio e como ela difere de um simples número?"
    )


def diagnostic_turn(
    conversation_summary: str,
    student_answer: str,
    block_hint: str,
) -> tuple[str, dict[str, Any]]:
    """
    Returns assistant message + metadata dict with keys:
    block_completed (bool), identified_level (str|None), done (bool)
    """
    settings = get_settings()
    system = (
        "Você é o BrainAgent aplicando um diagnóstico de entrada em blocos A–D (MasterAI Academy). "
        "Tom: professor sênior direto, português BR, exemplos fintech quando útil.\n"
        "Após cada resposta do aluno: (1) avalie brevemente se a resposta indica domínio mínimo "
        "para avançar o bloco atual; (2) ou faça a próxima pergunta do mesmo bloco; "
        "ou (3) encerre com nível estimado.\n"
        "Níveis possíveis: level_0 … level_10 (use exatamente esse formato).\n"
        "NO FINAL da sua mensagem, inclua UMA linha JSON em markdown code fence assim:\n"
        "```json\n"
        '{"done":false,"block_completed":false,"next_block":"A","identified_level":null}\n'
        "```\n"
        "Quando o diagnóstico estiver completo: done=true, identified_level preenchido (ex.: level_1)."
    )
    user = (
        f"Contexto da sessão:\n{conversation_summary}\n\n"
        f"Bloco atual sugerido: {block_hint}\n\n"
        f"Última resposta do aluno:\n{student_answer}\n"
    )
    raw = llm_complete(system, user, settings.brainagent_max_tokens_evaluation)
    meta = _extract_diagnostic_meta(raw)
    clean = _strip_json_fence(raw)
    return clean, meta


def _strip_json_fence(text: str) -> str:
    """Remove trailing ```json ... ``` block from model output."""
    fence = re.search(r"```json\s*[\s\S]*?```\s*$", text)
    if fence:
        return text[: fence.start()].strip()
    return text.strip()


def _extract_diagnostic_meta(text: str) -> dict[str, Any]:
    m = re.search(r"```json\s*([\s\S]*?)```", text)
    default = {"done": False, "block_completed": False, "next_block": "A", "identified_level": None}
    if not m:
        return default
    try:
        return {**default, **json.loads(m.group(1))}
    except json.JSONDecodeError:
        return default


def generate_exercise_payload(
    lesson_title: str,
    exercise_base: dict[str, Any],
    profile: str | None,
    avg_score: float | None,
) -> dict[str, Any]:
    settings = get_settings()
    variant = "padrao"
    if avg_score is not None:
        if avg_score < 0.60:
            variant = "scaffolded"
        elif avg_score >= 0.80:
            variant = "desafio"

    system = (
        "Você gera um exercício personalizado para MasterAI Academy. "
        "Responda APENAS com JSON válido, chaves: context, question, data, hint, rationale."
    )
    user = json.dumps(
        {
            "lesson_title": lesson_title,
            "exercise_base": exercise_base,
            "student_profile": profile or "analytics",
            "variant": variant,
        },
        ensure_ascii=False,
    )
    raw = llm_complete(system, user, settings.brainagent_max_tokens_evaluation)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {
            "context": exercise_base.get("base_context", ""),
            "question": exercise_base.get("base_question", ""),
            "data": "",
            "hint": "",
            "rationale": "Fallback — parse error",
        }
    data["variant"] = variant
    return data


def evaluate_submission_payload(
    lesson_title: str,
    question: str,
    rubric: str,
    student_answer: str,
) -> dict[str, Any]:
    settings = get_settings()
    system = (
        "Avalie a resposta do aluno. Responda APENAS JSON com chaves numéricas 0-1: "
        "technical, methodological, antipatterns, interpretation, composite; "
        "e 'feedback' (texto curto em português)."
    )
    user = json.dumps(
        {
            "lesson": lesson_title,
            "question": question,
            "reference_rubric": rubric,
            "answer": student_answer,
        },
        ensure_ascii=False,
    )
    raw = llm_complete(system, user, settings.brainagent_max_tokens_evaluation)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {
            "technical": 0.7,
            "methodological": 0.7,
            "antipatterns": 0.7,
            "interpretation": 0.7,
            "composite": 0.7,
            "feedback": raw[:1500],
        }


def chat_with_tutor(student_id: uuid.UUID, message: str, lesson_id: str | None, profile: str | None) -> str:
    """Chat tutor usando o mesmo LLM configurado (sem BrainAgent V3 local por padrão)."""
    settings = get_settings()
    system_parts = [
        ACADEMY_TEACHER_IDENTITY_EN.strip(),
        ACADEMY_TEACHER_CONTEXT_BASE.strip(),
        f"student_id={student_id}",
    ]
    if profile:
        system_parts.append(f"Perfil declarado: {profile}.")
    system = "\n\n".join(system_parts)

    user = message.strip()
    if lesson_id:
        user = f"[contexto: aula={lesson_id}]\n{user}"

    return llm_complete(system, user, settings.brainagent_max_tokens_chat)


def recommend_next_lesson(
    completed_summary: str,
    available_ids: list[str],
) -> tuple[str, str, str]:
    settings = get_settings()
    system = (
        "Escolha a próxima aula dado o progresso. Responda APENAS JSON: "
        '{"lesson_id":"","title":"","reason":""}'
    )
    user = json.dumps(
        {"available_lesson_ids": available_ids, "history": completed_summary},
        ensure_ascii=False,
    )
    raw = llm_complete(system, user, settings.brainagent_max_tokens_recommendation)
    try:
        d = json.loads(raw)
        return d.get("lesson_id", available_ids[0]), d.get("title", ""), d.get("reason", "")
    except (json.JSONDecodeError, IndexError):
        lid = available_ids[0] if available_ids else "unknown"
        return lid, "", "Recomendação fallback"
