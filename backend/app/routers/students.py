"""Current student profile and dashboard overview."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_student
from app.models import Lesson, ProceduralMemory, Student, StudentLessonProgress
from app.services.student_service import touch_activity
from app.services.unlock_service import refresh_unlocks_for_student

router = APIRouter()


@router.get("/students/me")
def get_me(
    db: Annotated[Session, Depends(get_db)],
    student: Annotated[Student, Depends(get_current_student)],
) -> dict:
    touch_activity(db, student)
    completed = db.execute(
        select(func.count())
        .select_from(StudentLessonProgress)
        .where(
            StudentLessonProgress.student_id == student.id,
            StudentLessonProgress.status == "completed",
        )
    ).scalar() or 0
    available = db.execute(
        select(func.count())
        .select_from(StudentLessonProgress)
        .where(
            StudentLessonProgress.student_id == student.id,
            StudentLessonProgress.status == "available",
        )
    ).scalar() or 0
    locked = db.execute(
        select(func.count())
        .select_from(StudentLessonProgress)
        .where(
            StudentLessonProgress.student_id == student.id,
            StudentLessonProgress.status == "locked",
        )
    ).scalar() or 0
    avg = db.execute(
        select(func.avg(StudentLessonProgress.score_composite)).where(
            StudentLessonProgress.student_id == student.id,
            StudentLessonProgress.status == "completed",
        )
    ).scalar()

    return {
        "id": str(student.id),
        "name": student.name,
        "email": student.email,
        "profile": student.profile,
        "current_level": student.current_level,
        "total_xp": student.total_xp,
        "streak_days": student.streak_days,
        "last_activity_at": student.last_activity_at.isoformat()
        if student.last_activity_at
        else None,
        "diagnostic_status": student.diagnostic_status,
        "onboarding_done": student.onboarding_done,
        "stats": {
            "lessons_completed": int(completed),
            "lessons_available": int(available),
            "lessons_locked": int(locked),
            "avg_score": round(float(avg), 2) if avg is not None else None,
        },
    }


@router.get("/students/me/overview")
def get_overview(
    db: Annotated[Session, Depends(get_db)],
    student: Annotated[Student, Depends(get_current_student)],
) -> dict:
    refresh_unlocks_for_student(db, student.id)
    touch_activity(db, student)

    next_row = db.execute(
        select(Lesson, StudentLessonProgress)
        .join(
            StudentLessonProgress,
            (StudentLessonProgress.lesson_id == Lesson.id)
            & (StudentLessonProgress.student_id == student.id),
        )
        .where(
            StudentLessonProgress.status.in_(("available", "in_progress")),
            Lesson.is_active == True,  # noqa: E712
        )
        .order_by(Lesson.level_number, Lesson.order_in_level)
        .limit(1)
    ).first()

    next_lesson = None
    if next_row:
        les, _ = next_row
        next_lesson = {
            "id": les.id,
            "title": les.title,
            "level_number": les.level_number,
            "xp_reward": les.xp_reward,
            "duration_min": les.duration_min,
        }

    lvl = student.current_level or "level_0"
    num = int(lvl.split("_")[1])
    total_lvl = db.execute(
        select(func.count()).select_from(Lesson).where(Lesson.level_number == num, Lesson.is_active == True)  # noqa: E712
    ).scalar() or 1
    done_lvl = db.execute(
        select(func.count())
        .select_from(StudentLessonProgress)
        .join(Lesson, Lesson.id == StudentLessonProgress.lesson_id)
        .where(
            StudentLessonProgress.student_id == student.id,
            Lesson.level_number == num,
            StudentLessonProgress.status == "completed",
        )
    ).scalar() or 0

    recent = db.execute(
        select(Lesson.id, Lesson.title, StudentLessonProgress.score_composite, StudentLessonProgress.completed_at)
        .join(Lesson, Lesson.id == StudentLessonProgress.lesson_id)
        .where(
            StudentLessonProgress.student_id == student.id,
            StudentLessonProgress.status == "completed",
        )
        .order_by(StudentLessonProgress.completed_at.desc())
        .limit(3)
    ).all()

    procedural = db.execute(
        select(ProceduralMemory.pattern)
        .where(ProceduralMemory.student_id == student.id)
        .order_by(ProceduralMemory.updated_at.desc())
        .limit(3)
    ).scalars().all()

    mastered = db.execute(
        select(func.count())
        .select_from(StudentLessonProgress)
        .where(
            StudentLessonProgress.student_id == student.id,
            StudentLessonProgress.status == "completed",
            StudentLessonProgress.score_composite >= 0.75,
        )
    ).scalar() or 0

    return {
        "next_lesson": next_lesson,
        "brainagent_message": "Continue na sequência — consistência importa mais que velocidade.",
        "current_level": {
            "level": lvl,
            "progress_pct": round(100.0 * done_lvl / total_lvl, 1) if total_lvl else 0,
            "lessons_done": int(done_lvl),
            "lessons_total": int(total_lvl),
        },
        "recent_activity": [
            {
                "lesson_id": r[0],
                "title": r[1],
                "score": float(r[2]) if r[2] is not None else None,
                "completed_at": r[3].isoformat() if r[3] else None,
            }
            for r in recent
        ],
        "memory_snapshot": {
            "procedural": list(procedural),
            "concepts_mastered": int(mastered),
            "concepts_in_progress": 0,
        },
    }
