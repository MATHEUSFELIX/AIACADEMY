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
from app.memory.redis_cache import (
    pending_exercise_delete,
    pending_exercise_get,
    pending_exercise_set,
    rate_limit_check,
)
from app.models import ExerciseSubmission, Lesson, Student, StudentLessonProgress, XpTransaction
from app.services.brainagent_service import evaluate_submission_payload, generate_exercise_payload
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
    if body.used_hint:
        xp = max(0, xp_base - 10)
    if composite >= 0.95:
        xp = int(xp * 1.2)

    variant = pending.get("variant", "padrao")
    sub = ExerciseSubmission(
        student_id=student.id,
        lesson_id=lesson_id,
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
    unlocked: list[str] = []
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
        if composite >= 0.75:
            prog.status = "completed"
            prog.completed_at = datetime.now(timezone.utc)
        student.total_xp += xp
        db.add(
            XpTransaction(
                student_id=student.id,
                amount=xp,
                reason="lesson_exercise",
                lesson_id=lesson_id,
            )
        )

    db.commit()
    pending_exercise_delete(body.exercise_id)
    refresh_unlocks_for_student(db, student.id)
    maybe_advance_level(db, student)

    if composite >= 0.75:
        for lid in lesson.connections or []:
            other = db.execute(
                select(StudentLessonProgress).where(
                    StudentLessonProgress.student_id == student.id,
                    StudentLessonProgress.lesson_id == lid,
                )
            ).scalar_one_or_none()
            if other and other.status == "locked":
                # unlocked via refresh_unlocks
                pass

    refresh_unlocks_for_student(db, student.id)

    return {
        "scores": {
            "technical": tech,
            "methodological": meth,
            "antipatterns": anti,
            "interpretation": inter,
            "composite": composite,
        },
        "feedback": feedback,
        "xp_earned": xp,
        "lesson_completed": composite >= 0.75,
        "unlocked_lessons": unlocked,
        "memory_updated": {
            "episodic": True,
            "procedural": [feedback[:80]] if feedback else [],
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
