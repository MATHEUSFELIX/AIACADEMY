"""BrainAgent chat, recommendations, memory snapshot."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.deps import get_current_student
from app.memory.redis_cache import cache_get_json, cache_set_json, rate_limit_check
from app.models import EpisodicMemory, Lesson, ProceduralMemory, Student, StudentLessonProgress
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

    answer = chat_with_tutor(
        student.id,
        body.message,
        lesson_id=body.context_lesson_id,
        profile=student.profile,
    )

    episodic_n = db.execute(
        select(func.count()).select_from(EpisodicMemory).where(EpisodicMemory.student_id == student.id)
    ).scalar()

    proc_n = db.execute(
        select(func.count()).select_from(ProceduralMemory).where(ProceduralMemory.student_id == student.id)
    ).scalar()

    return {
        "response": answer,
        "relevant_lessons": [],
        "memory_used": {
            "episodic_items": int(episodic_n or 0),
            "procedural_patterns": int(proc_n or 0),
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
        select(Lesson.id, Lesson.title)
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

    ids = [r[0] for r in avail]
    summary = f"student={student.id} level={student.current_level}"
    lid, title, reason = recommend_next_lesson(summary, ids)

    title_match = next((r[1] for r in avail if r[0] == lid), title or "")
    out = {
        "lesson_id": lid,
        "title": title_match,
        "reason": reason,
        "alternatives": [],
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
        "objective": {
            "goal": "Dominar trilha Analytics",
            "progress": 0.04,
            "active": True,
        },
    }
