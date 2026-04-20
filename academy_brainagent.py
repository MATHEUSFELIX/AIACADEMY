"""
MasterAI Academy — BrainAgent V3 como professor (tutor)

Usa ``brainagent_v3.BrainAgentV3`` + ``AgentConfig`` com persona pedagógica alinhada a
CLAUDE.md: professor sênior, direto, exemplos fintech Brasil, sem elogios vazios.

Uso típico (serviço FastAPI): um agente por aluno isolado por ``project=academy_<student_id>``.

    from academy_brainagent import build_academy_teacher_config, create_academy_teacher_agent

    agent = create_academy_teacher_agent(
        student_id="uuid-do-aluno",
        profile="analytics",
    )
    resp = agent.run("Explique quando prefiro DiD em vez de antes-e-depois simples.")
"""

from __future__ import annotations

from pathlib import Path

from brainagent_v3 import AgentConfig, AgentResponse, BrainAgentV3


# ── Identidade (primeira linha do system prompt do LLMAdapter) ───────────────

ACADEMY_TEACHER_IDENTITY_EN = (
    "You are the BrainAgent tutor for MasterAI Academy — a senior data/AI instructor "
    "for an internal Brazilian consulting team. You teach with clarity and rigor; "
    "you do not flatter. Respond in Portuguese unless the student writes in English."
)

# ── Contexto de domínio (system_context — regras pedagógicas e operacionais) ─

ACADEMY_TEACHER_CONTEXT_BASE = """
Domínio: MasterAI Academy — plataforma interna de IA e dados (não é produto público).

Seu papel:
- Conduzir diagnóstico conversacional (blocos A→D): uma pergunta por vez; avaliar raciocínio em texto livre.
- Ensinar conceitos com foco aplicável (PicPay, Santander, Inter, C6 Bank, Mastercard Brasil quando fizer sentido).
- Nos exercícios: NÃO entregar a solução completa pronta para copiar; guie com perguntas, contra-exemplos e checkpoints.
  Se o enunciado pedir avaliação objetiva (ex.: cálculo DiD), avalie método e interpretação; aponte erro específico.
- Adaptar profundidade ao perfil do aluno quando informado:
  analytics → PySpark, Delta Lake, SQL, pipelines
  marketing → campanhas, incrementality, segmentação
  strategy → decisão executiva, ROI, narrativa
  c_level → trade-offs e governança sem detalhe operacional excessivo
  produto → métricas de produto, experimentação, funil

Memória local (arquivos .brainagent): complementa o PostgreSQL/Chroma da plataforma.
Persistir preferências úteis; não contradizer dados canônicos do backend.

Tom: direto, respeitoso, preciso. Evite "Ótima pergunta!" e hype. Use estrutura curta (títulos claros quando ajudar).
"""


def build_academy_teacher_config(
    student_id: str,
    *,
    profile: str | None = None,
    lesson_id: str | None = None,
    extra_context: str = "",
    storage_dir: str | Path = ".brainagent",
    model: str = "claude-sonnet-4-20250514",
    max_tokens: int = 2048,
    enable_dream_cycle: bool = False,
    enable_council: bool = False,
    use_vector_store: bool = False,
) -> AgentConfig:
    """
    Monta AgentConfig para tutor Academy.

    - ``enable_dream_cycle=False`` por padrão (adequado a workers HTTP sem thread daemon por worker).
    - ``enable_council=False`` por padrão (evita N chamadas extras ao Claude por turno).
    - Isolamento por aluno: ``project=f\"academy_{student_id}\"``.
    """
    student_id = student_id.strip()
    if not student_id:
        raise ValueError("student_id é obrigatório")

    ctx_parts = [ACADEMY_TEACHER_CONTEXT_BASE.strip()]
    if profile:
        ctx_parts.append(f"Perfil declarado do aluno (onboarding): {profile}.")
    if lesson_id:
        ctx_parts.append(f"Aula/conceito atual na sessão (quando aplicável): {lesson_id}.")
    if extra_context.strip():
        ctx_parts.append(extra_context.strip())

    return AgentConfig(
        project=f"academy_{student_id}",
        model=model,
        max_tokens=max_tokens,
        storage_dir=str(storage_dir),
        system_context="\n\n".join(ctx_parts),
        agent_identity=ACADEMY_TEACHER_IDENTITY_EN,
        enable_dream_cycle=enable_dream_cycle,
        enable_council=enable_council,
        use_vector_store=use_vector_store,
    )


def create_academy_teacher_agent(
    student_id: str,
    *,
    profile: str | None = None,
    lesson_id: str | None = None,
    extra_context: str = "",
    storage_dir: str | Path = ".brainagent",
    model: str = "claude-sonnet-4-20250514",
    max_tokens: int = 2048,
    enable_dream_cycle: bool = False,
    enable_council: bool = False,
    use_vector_store: bool = False,
) -> BrainAgentV3:
    """Instancia BrainAgentV3 com config de professor Academy."""
    cfg = build_academy_teacher_config(
        student_id,
        profile=profile,
        lesson_id=lesson_id,
        extra_context=extra_context,
        storage_dir=storage_dir,
        model=model,
        max_tokens=max_tokens,
        enable_dream_cycle=enable_dream_cycle,
        enable_council=enable_council,
        use_vector_store=use_vector_store,
    )
    return BrainAgentV3(cfg)


def teacher_chat_turn(
    agent: BrainAgentV3,
    student_message: str,
    *,
    lesson_id: str | None = None,
) -> str:
    """
    Um turno de chat tutor. Opcionalmente prefixa o contexto da aula na query interna
    (classificador + memória ainda veem texto enriquecido).

    Retorna apenas o texto da resposta (equivalente a agent.run(...).answer).
    """
    q = student_message.strip()
    if lesson_id:
        q = f"[contexto: aula={lesson_id}]\n{q}"
    resp: AgentResponse = agent.run(q)
    return resp.answer
