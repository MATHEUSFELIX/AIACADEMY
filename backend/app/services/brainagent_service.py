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

    variant_instruction = ""
    if variant == "scaffolded":
        variant_instruction = (
            "Variante SCAFFOLDED: forneça código quase completo com lacunas para preencher. "
            "Inclua dicas automáticas no enunciado. Use dataset menor com menos variáveis."
        )
    elif variant == "desafio":
        variant_instruction = (
            "Variante DESAFIO: inclua um twist no enunciado — viola uma suposição esperada "
            "ou insere um bug proposital que o aluno deve detectar. "
            "Não forneça hints. Use dataset com problemas reais para o aluno identificar."
        )
    else:
        variant_instruction = (
            "Variante PADRÃO: enunciado completo, código em branco. "
            "Hints disponíveis mas custam -10 XP. Dataset realista."
        )

    system = (
        "Você gera um exercício personalizado para MasterAI Academy. "
        "Responda APENAS com JSON válido, chaves: context, question, data, hint, rationale.\n"
        f"{variant_instruction}"
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


def chat_with_tutor(
    student_id: uuid.UUID,
    message: str,
    lesson_id: str | None,
    profile: str | None,
    episodic_context: list[dict] | None = None,
    procedural_patterns: list[dict] | None = None,
    brainagent_notes: str | None = None,
) -> str:
    """Chat tutor with full memory context injected into system prompt."""
    settings = get_settings()
    system_parts = [
        ACADEMY_TEACHER_IDENTITY_EN.strip(),
        ACADEMY_TEACHER_CONTEXT_BASE.strip(),
        f"student_id={student_id}",
    ]
    if profile:
        system_parts.append(f"Perfil declarado: {profile}.")

    if brainagent_notes:
        system_parts.append(
            f"Notas do diagnóstico inicial:\n{brainagent_notes[:500]}"
        )

    if episodic_context:
        lines = []
        for ep in episodic_context[:8]:
            score = ep.get("score", "?")
            action = ep.get("action", "")
            lines.append(f"  - {action} (score={score})")
        system_parts.append("Histórico recente do aluno:\n" + "\n".join(lines))

    if procedural_patterns:
        lines = []
        for pp in procedural_patterns[:5]:
            pattern = pp.get("pattern", "")
            confidence = pp.get("confidence", "?")
            category = pp.get("category", "")
            lines.append(f"  - [{category}] {pattern} (conf={confidence})")
        system_parts.append("Padrões aprendidos do aluno:\n" + "\n".join(lines))

    system = "\n\n".join(system_parts)

    user = message.strip()
    if lesson_id:
        user = f"[contexto: aula={lesson_id}]\n{user}"

    return llm_complete(system, user, settings.brainagent_max_tokens_chat)


def recommend_next_lesson(
    student_summary: str,
    available_lessons: list[dict],
) -> tuple[str, str, str]:
    """
    student_summary: string with level, profile, streak info
    available_lessons: list of {id, title, level_number, score_composite or None}
    Returns: (lesson_id, title, reason)
    """
    settings = get_settings()
    system = (
        "Escolha a melhor próxima aula dado o perfil e histórico do aluno. "
        "Responda APENAS JSON: "
        '{"lesson_id":"","title":"","reason":""}'
    )
    user = json.dumps(
        {
            "student_summary": student_summary,
            "available_lessons": available_lessons,
        },
        ensure_ascii=False,
    )
    raw = llm_complete(system, user, settings.brainagent_max_tokens_recommendation)
    try:
        d = json.loads(raw)
        lid = d.get("lesson_id", "")
        if not lid and available_lessons:
            lid = available_lessons[0]["id"]
        return lid, d.get("title", ""), d.get("reason", "")
    except (json.JSONDecodeError, IndexError):
        lid = available_lessons[0]["id"] if available_lessons else "unknown"
        return lid, "", "Recomendação fallback"


def extract_procedural_pattern(
    lesson_title: str,
    student_answer: str,
    feedback: str,
    composite_score: float,
    profile: str | None,
) -> dict[str, Any] | None:
    """
    Ask LLM to extract a reusable learning pattern from a high-score submission.
    Returns {pattern, category, confidence} or None if not applicable.
    """
    if composite_score < 0.75:
        return None

    settings = get_settings()
    system = (
        "Dado um exercício avaliado, extraia UM padrão de aprendizado reutilizável do aluno. "
        "Responda APENAS JSON: "
        '{"pattern":"frase curta descrevendo o que o aluno demonstrou","category":"sql|ml|stats|viz|causal|geral","confidence":0.8}\n'
        "Se não houver padrão relevante, responda: null"
    )
    user = json.dumps(
        {
            "lesson": lesson_title,
            "profile": profile or "analytics",
            "answer_summary": student_answer[:300],
            "feedback": feedback[:300],
            "score": composite_score,
        },
        ensure_ascii=False,
    )
    raw = llm_complete(system, user, 300)
    raw = raw.strip()
    if raw.lower() == "null":
        return None
    try:
        d = json.loads(raw)
        if not isinstance(d, dict) or not d.get("pattern"):
            return None
        return d
    except json.JSONDecodeError:
        return None
