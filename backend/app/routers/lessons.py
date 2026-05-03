"""Lessons list, detail, start, exercise generate/submit/hint."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.deps import get_current_student
from app.memory.chroma_semantic import upsert_student_concept
from app.memory.redis_cache import (
    pending_exercise_delete,
    pending_exercise_get,
    pending_exercise_set,
    rate_limit_check,
)
from app.models import (
    EpisodicMemory,
    ExerciseSubmission,
    Lesson,
    ProceduralMemory,
    Student,
    StudentLessonProgress,
    XpTransaction,
)
from app.services.brainagent_service import (
    evaluate_submission_payload,
    extract_procedural_pattern,
    generate_exercise_payload,
)
from app.services.student_service import touch_activity
from app.services.unlock_service import (
    lesson_is_accessible,
    maybe_advance_level,
    refresh_unlocks_for_student,
)

router = APIRouter(prefix="/lessons")


class ExerciseSubmitIn(BaseModel):
    exercise_id: uuid.UUID
    answer: str = Field(..., min_length=1)
    used_hint: bool = False
    brainagent_mode: str = Field(default="guided", max_length=32)


LESSON_MODES: list[dict[str, str]] = [
    {
        "mode": "guided",
        "name": "Guiado",
        "description": "Resolucao passo a passo com foco no raciocinio correto.",
        "emoji": "BA",
        "icon": "guide",
    },
    {
        "mode": "socratic",
        "name": "Socratico",
        "description": "Perguntas direcionadas para testar hipoteses antes da resposta final.",
        "emoji": "?",
        "icon": "ask",
    },
    {
        "mode": "competitive",
        "name": "Competitivo",
        "description": "Compare sua solucao com um baseline do BrainAgent.",
        "emoji": "VS",
        "icon": "vs",
    },
    {
        "mode": "streaming",
        "name": "Raciocinio aberto",
        "description": "Feedback explicita os passos de avaliacao do BrainAgent.",
        "emoji": "AI",
        "icon": "flow",
    },
    {
        "mode": "inner_monologue",
        "name": "Autonomia",
        "description": "Menos pistas e avaliacao de independencia na resolucao.",
        "emoji": "GO",
        "icon": "solo",
    },
    {
        "mode": "progressive",
        "name": "Progressivo",
        "description": "Consolida fundamentos antes de liberar desafios maiores.",
        "emoji": "UP",
        "icon": "level",
    },
]

SUPPORTED_LESSON_MODES = {mode["mode"] for mode in LESSON_MODES}


def _mode_result_for(mode: str, composite: float) -> dict[str, Any]:
    if mode == "competitive":
        agent_score = 0.78
        return {
            "winner": "student" if composite >= agent_score else "brainagent",
            "student_score": round(composite, 2),
            "agent_score": agent_score,
        }
    if mode == "socratic":
        return {
            "next_question": (
                "Qual suposicao precisa estar verdadeira para sua conclusao causal se sustentar?"
                if composite < 0.75
                else "Como voce explicaria esta decisao para um diretor nao tecnico?"
            )
        }
    if mode == "streaming":
        return {
            "streaming_thoughts": (
                "Avaliei tecnica, metodologia, antipadroes e interpretacao antes do score composto."
            )
        }
    if mode == "inner_monologue":
        return {
            "hints_used": 0,
            "independence_level": "alta" if composite >= 0.75 else "precisa de scaffold",
        }
    if mode == "progressive":
        return {
            "next_unlocked_modes": ["competitive", "inner_monologue"] if composite >= 0.75 else ["guided"],
        }
    return {"summary": "Feedback guiado concluido pelo BrainAgent."}


def _lesson_public(
    lesson: Lesson,
    prog: StudentLessonProgress | None,
) -> dict[str, Any]:
    return {
        "id": lesson.id,
        "title": lesson.title,
        "module": lesson.module,
        "level_number": lesson.level_number,
        "order_in_level": lesson.order_in_level,
        "xp_reward": lesson.xp_reward,
        "duration_min": lesson.duration_min,
        "status": prog.status if prog else "locked",
        "score_composite": float(prog.score_composite) if prog and prog.score_composite else None,
        "prerequisites": list(lesson.prerequisites or []),
        "kb_confidence": float(lesson.kb_confidence),
    }


@router.get("/{lesson_id}/modes")
def get_lesson_modes(
    lesson_id: str,
    db: Annotated[Session, Depends(get_db)],
    student: Annotated[Student, Depends(get_current_student)],
) -> dict:
    lesson = db.get(Lesson, lesson_id)
    if not lesson or not lesson_is_accessible(db, student.id, lesson_id):
        raise HTTPException(status_code=403, detail="LESSON_LOCKED")

    return {"data": {"modes": LESSON_MODES}}


@router.post("/{lesson_id}/recommend-mode")
def recommend_lesson_mode(
    lesson_id: str,
    db: Annotated[Session, Depends(get_db)],
    student: Annotated[Student, Depends(get_current_student)],
) -> dict:
    lesson = db.get(Lesson, lesson_id)
    if not lesson or not lesson_is_accessible(db, student.id, lesson_id):
        raise HTTPException(status_code=403, detail="LESSON_LOCKED")

    completed_scores = db.execute(
        select(StudentLessonProgress.score_composite)
        .where(
            StudentLessonProgress.student_id == student.id,
            StudentLessonProgress.status == "completed",
        )
        .limit(20)
    ).scalars().all()
    scores = [float(score) for score in completed_scores if score is not None]
    avg_score = sum(scores) / len(scores) if scores else None

    if avg_score is not None and avg_score >= 0.85:
        mode = "competitive"
        reason = "Seu historico permite um desafio com comparacao contra baseline do BrainAgent."
    elif avg_score is not None and avg_score < 0.65:
        mode = "guided"
        reason = "O modo guiado reduz risco de travar e reforca o raciocinio passo a passo."
    else:
        mode = "socratic"
        reason = "Perguntas direcionadas ajudam a validar suposicoes antes da resposta final."

    return {"data": {"recommended_mode": mode, "reason": reason}}


@router.get("")
def list_lessons(
    db: Annotated[Session, Depends(get_db)],
    student: Annotated[Student, Depends(get_current_student)],
    level: int | None = None,
    module: str | None = None,
    status_filter: str | None = Query(None, alias="status"),
) -> dict:
    refresh_unlocks_for_student(db, student.id)
    touch_activity(db, student)

    q = select(Lesson).where(Lesson.is_active == True)  # noqa: E712
    if level is not None:
        q = q.where(Lesson.level_number == level)
    if module:
        q = q.where(Lesson.module == module)

    lessons = db.execute(q.order_by(Lesson.level_number, Lesson.order_in_level)).scalars().all()
    total_db = db.execute(select(func.count()).select_from(Lesson).where(Lesson.is_active == True)).scalar()  # noqa: E712
    out = []
    for lesson in lessons:
        prog = db.execute(
            select(StudentLessonProgress).where(
                StudentLessonProgress.student_id == student.id,
                StudentLessonProgress.lesson_id == lesson.id,
            )
        ).scalar_one_or_none()
        row = _lesson_public(lesson, prog)
        if status_filter and row["status"] != status_filter:
            continue
        out.append(row)

    return {"lessons": out, "total": int(total_db or 0)}


@router.get("/{lesson_id}")
def get_lesson(
    lesson_id: str,
    db: Annotated[Session, Depends(get_db)],
    student: Annotated[Student, Depends(get_current_student)],
) -> dict:
    refresh_unlocks_for_student(db, student.id)
    lesson = db.get(Lesson, lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail=f"Lesson {lesson_id} not found")

    prog = db.execute(
        select(StudentLessonProgress).where(
            StudentLessonProgress.student_id == student.id,
            StudentLessonProgress.lesson_id == lesson_id,
        )
    ).scalar_one_or_none()

    if not lesson_is_accessible(db, student.id, lesson_id):
        raise HTTPException(status_code=403, detail="LESSON_LOCKED")

    return {
        "id": lesson.id,
        "title": lesson.title,
        "subtitle": lesson.subtitle,
        "module": lesson.module,
        "level_number": lesson.level_number,
        "xp_reward": lesson.xp_reward,
        "duration_min": lesson.duration_min,
        "status": prog.status if prog else "locked",
        "hook_config": lesson.hook_config,
        "widget_config": lesson.widget_config,
        "kb_content": lesson.kb_content,
        "prerequisites": list(lesson.prerequisites or []),
        "connections": list(lesson.connections or []),
    }


@router.post("/{lesson_id}/start")
def start_lesson(
    lesson_id: str,
    db: Annotated[Session, Depends(get_db)],
    student: Annotated[Student, Depends(get_current_student)],
) -> dict:
    if not lesson_is_accessible(db, student.id, lesson_id):
        raise HTTPException(status_code=403, detail="LESSON_LOCKED")

    prog = db.execute(
        select(StudentLessonProgress).where(
            StudentLessonProgress.student_id == student.id,
            StudentLessonProgress.lesson_id == lesson_id,
        )
    ).scalar_one_or_none()
    if not prog:
        raise HTTPException(status_code=404, detail="Progress not found")

    if prog.status == "locked":
        prog.status = "available"

    if prog.status in ("available", "in_progress"):
        prog.status = "in_progress"
        if prog.started_at is None:
            prog.started_at = datetime.now(timezone.utc)

    db.commit()
    return {
        "lesson_id": lesson_id,
        "status": prog.status,
        "started_at": prog.started_at.isoformat() if prog.started_at else None,
    }


@router.post("/{lesson_id}/exercise/generate")
def generate_exercise(
    lesson_id: str,
    db: Annotated[Session, Depends(get_db)],
    student: Annotated[Student, Depends(get_current_student)],
) -> dict:
    settings = get_settings()
    rate_limit_check(student.id, "brainagent", settings.brainagent_rate_limit_per_hour)

    lesson = db.get(Lesson, lesson_id)
    if not lesson or not lesson_is_accessible(db, student.id, lesson_id):
        raise HTTPException(status_code=403, detail="LESSON_LOCKED")

    avg_row = db.execute(
        select(StudentLessonProgress.score_composite)
        .where(
            StudentLessonProgress.student_id == student.id,
            StudentLessonProgress.status == "completed",
        )
        .limit(50)
    ).scalars().all()
    avg = sum(float(x) for x in avg_row if x is not None) / len(avg_row) if avg_row else None

    base = lesson.exercise_base if isinstance(lesson.exercise_base, dict) else {}
    gen = generate_exercise_payload(lesson.title, base, student.profile, avg)
    eid = uuid.uuid4()
    variant = gen.get("variant", "padrao")
    pending_exercise_set(
        eid,
        {
            "student_id": str(student.id),
            "lesson_id": lesson_id,
            "variant": variant,
            "payload": gen,
        },
    )

    xp_base = lesson.xp_reward
    return {
        "exercise_id": str(eid),
        "variant": variant,
        "context": gen.get("context", ""),
        "question": gen.get("question", ""),
        "data": gen.get("data", ""),
        "has_hint": bool(gen.get("hint")),
        "xp_if_no_hint": xp_base,
        "xp_if_hint": max(0, xp_base - 10),
        "rationale": gen.get("rationale", ""),
    }


@router.post("/{lesson_id}/exercise/submit")
def submit_exercise(
    lesson_id: str,
    body: ExerciseSubmitIn,
    db: Annotated[Session, Depends(get_db)],
    student: Annotated[Student, Depends(get_current_student)],
) -> dict:
    settings = get_settings()
    rate_limit_check(student.id, f"exercise_submit:{lesson_id}", 10)

    pending = pending_exercise_get(body.exercise_id)
    if not pending or pending.get("student_id") != str(student.id) or pending.get("lesson_id") != lesson_id:
        raise HTTPException(status_code=404, detail="Invalid exercise_id")

    mode = body.brainagent_mode if body.brainagent_mode in SUPPORTED_LESSON_MODES else "guided"
    lesson = db.get(Lesson, lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    base = lesson.exercise_base if isinstance(lesson.exercise_base, dict) else {}
    rubric = base.get("rubric_summary", "") or base.get("reference_solution", "") or ""

    payload = pending["payload"]
    eval_res = evaluate_submission_payload(
        lesson.title,
        payload.get("question", ""),
        rubric,
        body.answer,
    )
    composite = float(eval_res.get("composite", 0.75))
    tech = float(eval_res.get("technical", composite))
    meth = float(eval_res.get("methodological", composite))
    anti = float(eval_res.get("antipatterns", composite))
    inter = float(eval_res.get("interpretation", composite))
    feedback = str(eval_res.get("feedback", ""))

    xp_base = lesson.xp_reward
    xp = xp_base
    variant = pending.get("variant", "padrao")

    if body.used_hint:
        xp = max(0, xp_base - 10)
    if composite >= 0.95:
        xp = int(xp * 1.2)
    if variant == "desafio" and composite >= 0.75:
        xp = int(xp * 1.3)

    attempt_number = db.execute(
        select(func.count()).select_from(ExerciseSubmission).where(
            ExerciseSubmission.student_id == student.id,
            ExerciseSubmission.lesson_id == lesson_id,
        )
    ).scalar() or 0
    attempt_number += 1

    sub = ExerciseSubmission(
        student_id=student.id,
        lesson_id=lesson_id,
        attempt_number=attempt_number,
        student_answer=body.answer,
        exercise_variant=variant,
        generated_exercise=payload,
        score_technical=tech,
        score_methodological=meth,
        score_antipatterns=anti,
        score_interpretation=inter,
        score_composite=composite,
        brainagent_feedback=feedback,
        used_hint=body.used_hint,
        xp_earned=xp,
    )
    db.add(sub)

    prog = db.execute(
        select(StudentLessonProgress).where(
            StudentLessonProgress.student_id == student.id,
            StudentLessonProgress.lesson_id == lesson_id,
        )
    ).scalar_one_or_none()

    lesson_completed = composite >= 0.75
    if prog:
        prog.score_technical = tech
        prog.score_methodological = meth
        prog.score_antipatterns = anti
        prog.score_interpretation = inter
        prog.score_composite = composite
        prog.variant_used = variant
        prog.used_hint = body.used_hint
        prog.xp_earned = xp
        prog.attempts = (prog.attempts or 0) + 1
        if lesson_completed:
            prog.status = "completed"
            prog.completed_at = datetime.now(timezone.utc)
        student.total_xp = (student.total_xp or 0) + xp
        db.add(
            XpTransaction(
                student_id=student.id,
                amount=xp,
                reason="lesson_exercise",
                lesson_id=lesson_id,
            )
        )

    db.add(
        EpisodicMemory(
            student_id=student.id,
            lesson_id=lesson_id,
            context=f"lesson={lesson_id} variant={variant}",
            action=f"exercise_submit score={composite:.2f}",
            outcome=feedback[:500] if feedback else None,
            valence=composite,
            importance=min(1.0, composite + 0.1),
        )
    )

    db.commit()
    pending_exercise_delete(body.exercise_id)
    refresh_unlocks_for_student(db, student.id)
    maybe_advance_level(db, student)

    procedural_written: list[str] = []
    if lesson_completed:
        pattern_data = extract_procedural_pattern(
            lesson.title,
            body.answer,
            feedback,
            composite,
            student.profile,
        )
        if pattern_data:
            existing = db.execute(
                select(ProceduralMemory).where(
                    ProceduralMemory.student_id == student.id,
                    ProceduralMemory.pattern == pattern_data["pattern"],
                )
            ).scalar_one_or_none()
            if existing:
                existing.confidence = min(1.0, float(existing.confidence) + 0.05)
                existing.evidence_count = (existing.evidence_count or 1) + 1
            else:
                db.add(
                    ProceduralMemory(
                        student_id=student.id,
                        pattern=pattern_data["pattern"],
                        category=pattern_data.get("category", "geral"),
                        confidence=float(pattern_data.get("confidence", 0.7)),
                        evidence_count=1,
                    )
                )
            db.commit()
            procedural_written.append(pattern_data["pattern"])

        upsert_student_concept(
            str(student.id),
            lesson_id,
            f"{lesson.title}: score={composite:.2f} variant={variant}",
            {"score": composite, "variant": variant, "lesson_id": lesson_id},
        )

    return {
        "scores": {
            "technical": tech,
            "methodological": meth,
            "antipatterns": anti,
            "interpretation": inter,
            "composite": composite,
        },
        "mode": mode,
        "mode_result": _mode_result_for(mode, composite),
        "feedback": feedback,
        "xp_earned": xp,
        "lesson_completed": lesson_completed,
        "unlocked_lessons": [],
        "memory_updated": {
            "episodic": True,
            "procedural": procedural_written,
            "semantic": lesson_completed,
        },
    }


@router.get("/{lesson_id}/exercise/hint")
def exercise_hint(
    lesson_id: str,
    db: Annotated[Session, Depends(get_db)],
    student: Annotated[Student, Depends(get_current_student)],
) -> dict:
    lesson = db.get(Lesson, lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    base = lesson.exercise_base if isinstance(lesson.exercise_base, dict) else {}
    hint = base.get("hint", "") or "Releia o enunciado e verifique hipóteses explícitas."
    return {"hint": hint, "xp_deducted": 10}
