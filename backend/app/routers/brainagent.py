"""BrainAgent chat, recommendations, memory snapshot."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.deps import get_current_student
from app.memory.redis_cache import cache_get_json, cache_set_json, rate_limit_check
from app.models import (
    EpisodicMemory,
    Lesson,
    ProceduralMemory,
    Student,
    StudentLessonProgress,
    StudentObjective,
)
from app.services.brainagent_service import chat_with_tutor, recommend_next_lesson

router = APIRouter()


class ChatIn(BaseModel):
    message: str = Field(..., min_length=1)
    context_lesson_id: str | None = None


@router.post("/chat")
def brainagent_chat(
    body: ChatIn,
    db: Annotated[Session, Depends(get_db)],
    student: Annotated[Student, Depends(get_current_student)],
) -> dict:
    settings = get_settings()
    rate_limit_check(student.id, "brainagent", settings.brainagent_rate_limit_per_hour)

    episodic_rows = db.execute(
        select(EpisodicMemory.action, EpisodicMemory.valence, EpisodicMemory.created_at)
        .where(EpisodicMemory.student_id == student.id)
        .order_by(EpisodicMemory.created_at.desc())
        .limit(8)
    ).all()
    episodic_context = [
        {"action": r[0], "score": float(r[1]) if r[1] is not None else None}
        for r in episodic_rows
    ]

    procedural_rows = db.execute(
        select(ProceduralMemory.pattern, ProceduralMemory.confidence, ProceduralMemory.category)
        .where(ProceduralMemory.student_id == student.id)
        .order_by(ProceduralMemory.confidence.desc())
        .limit(5)
    ).all()
    procedural_patterns = [
        {"pattern": r[0], "confidence": float(r[1]) if r[1] is not None else None, "category": r[2]}
        for r in procedural_rows
    ]

    answer = chat_with_tutor(
        student.id,
        body.message,
        lesson_id=body.context_lesson_id,
        profile=student.profile,
        episodic_context=episodic_context,
        procedural_patterns=procedural_patterns,
        brainagent_notes=student.brainagent_notes if hasattr(student, "brainagent_notes") else None,
    )

    return {
        "response": answer,
        "relevant_lessons": [],
        "memory_used": {
            "episodic_items": len(episodic_rows),
            "procedural_patterns": len(procedural_rows),
        },
    }


@router.get("/recommend")
def brainagent_recommend(
    db: Annotated[Session, Depends(get_db)],
    student: Annotated[Student, Depends(get_current_student)],
) -> dict:
    settings = get_settings()
    cache_key = f"rec:{student.id}"
    cached = cache_get_json(cache_key)
    if cached:
        return cached

    rate_limit_check(student.id, "brainagent_rec", settings.brainagent_rate_limit_per_hour)

    avail = db.execute(
        select(Lesson.id, Lesson.title, Lesson.level_number)
        .join(
            StudentLessonProgress,
            (StudentLessonProgress.lesson_id == Lesson.id)
            & (StudentLessonProgress.student_id == student.id),
        )
        .where(
            StudentLessonProgress.status == "available",
            Lesson.is_active == True,  # noqa: E712
        )
        .order_by(Lesson.level_number, Lesson.order_in_level)
        .limit(15)
    ).all()

    completed = db.execute(
        select(
            Lesson.id,
            Lesson.title,
            StudentLessonProgress.score_composite,
            StudentLessonProgress.variant_used,
        )
        .join(
            StudentLessonProgress,
            (StudentLessonProgress.lesson_id == Lesson.id)
            & (StudentLessonProgress.student_id == student.id),
        )
        .where(StudentLessonProgress.status == "completed")
        .order_by(StudentLessonProgress.completed_at.desc())
        .limit(10)
    ).all()

    available_lessons = [
        {"id": r[0], "title": r[1], "level_number": r[2]}
        for r in avail
    ]

    completed_summary_parts = [
        f"{r[1]} (score={float(r[2]):.2f}, variant={r[3]})"
        for r in completed
        if r[2] is not None
    ]
    student_summary = (
        f"level={student.current_level} "
        f"profile={student.profile or 'analytics'} "
        f"streak={student.streak_days or 0}d "
        f"completed=[{'; '.join(completed_summary_parts[:5])}]"
    )

    lid, title, reason = recommend_next_lesson(student_summary, available_lessons)

    title_match = next((r[1] for r in avail if r[0] == lid), title or "")
    out = {
        "lesson_id": lid,
        "title": title_match,
        "reason": reason,
        "alternatives": [
            {"id": r[0], "title": r[1]}
            for r in avail
            if r[0] != lid
        ][:3],
    }
    cache_set_json(cache_key, out, settings.brainagent_cache_ttl)
    return out


@router.get("/memory")
def brainagent_memory(
    db: Annotated[Session, Depends(get_db)],
    student: Annotated[Student, Depends(get_current_student)],
) -> dict:
    episodic = db.execute(
        select(EpisodicMemory.action, EpisodicMemory.valence, EpisodicMemory.created_at)
        .where(EpisodicMemory.student_id == student.id)
        .order_by(EpisodicMemory.created_at.desc())
        .limit(10)
    ).all()

    procedural = db.execute(
        select(
            ProceduralMemory.pattern,
            ProceduralMemory.confidence,
            ProceduralMemory.category,
        )
        .where(ProceduralMemory.student_id == student.id)
        .order_by(ProceduralMemory.confidence.desc())
        .limit(10)
    ).all()

    mastered = db.execute(
        select(StudentLessonProgress.lesson_id)
        .where(
            StudentLessonProgress.student_id == student.id,
            StudentLessonProgress.status == "completed",
            StudentLessonProgress.score_composite >= 0.75,
        )
    ).scalars().all()

    conf_map = {
        row.lesson_id: float(row.score_composite or 0)
        for row in db.execute(
            select(StudentLessonProgress).where(StudentLessonProgress.student_id == student.id)
        ).scalars().all()
        if row.score_composite is not None
    }

    active_objective = db.execute(
        select(StudentObjective)
        .where(
            StudentObjective.student_id == student.id,
            StudentObjective.is_active == True,  # noqa: E712
        )
        .order_by(StudentObjective.priority.desc())
        .limit(1)
    ).scalar_one_or_none()

    if active_objective:
        objective_data = {
            "goal": active_objective.goal,
            "progress": float(active_objective.progress or 0),
            "active": True,
            "deadline": active_objective.deadline.isoformat() if active_objective.deadline else None,
        }
    else:
        objective_data = {
            "goal": None,
            "progress": 0.0,
            "active": False,
        }

    return {
        "episodic": [
            {"action": e[0], "score": float(e[1]), "created_at": e[2].isoformat() if e[2] else None}
            for e in episodic
        ],
        "procedural": [
            {"pattern": p[0], "confidence": float(p[1]), "category": p[2]} for p in procedural
        ],
        "semantic": {
            "concepts_mastered": list(mastered),
            "concepts_in_progress": [],
            "confidence_map": conf_map,
        },
        "objective": objective_data,
    }
