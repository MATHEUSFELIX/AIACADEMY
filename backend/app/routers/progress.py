"""Aggregate progress for the logged-in student."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_student
from app.models import Lesson, Student, StudentLessonProgress, XpTransaction

router = APIRouter()


@router.get("/me")
def progress_me(
    db: Annotated[Session, Depends(get_db)],
    student: Annotated[Student, Depends(get_current_student)],
) -> dict:
    by_module: dict[str, dict[str, float | int]] = {}
    for mod in ["A", "B", "C", "D", "E", "ZERO"]:
        total = db.execute(
            select(func.count()).select_from(Lesson).where(Lesson.module == mod, Lesson.is_active == True)  # noqa: E712
        ).scalar() or 0
        completed = db.execute(
            select(func.count())
            .select_from(StudentLessonProgress)
            .join(Lesson, Lesson.id == StudentLessonProgress.lesson_id)
            .where(
                StudentLessonProgress.student_id == student.id,
                Lesson.module == mod,
                StudentLessonProgress.status == "completed",
            )
        ).scalar() or 0
        avg = db.execute(
            select(func.avg(StudentLessonProgress.score_composite))
            .join(Lesson, Lesson.id == StudentLessonProgress.lesson_id)
            .where(
                StudentLessonProgress.student_id == student.id,
                Lesson.module == mod,
                StudentLessonProgress.status == "completed",
            )
        ).scalar()
        by_module[mod] = {
            "total": int(total),
            "completed": int(completed),
            "avg_score": round(float(avg), 2) if avg is not None else 0.0,
        }

    by_level = []
    for ln in range(0, 11):
        total = db.execute(
            select(func.count()).select_from(Lesson).where(Lesson.level_number == ln, Lesson.is_active == True)  # noqa: E712
        ).scalar() or 0
        completed = db.execute(
            select(func.count())
            .select_from(StudentLessonProgress)
            .join(Lesson, Lesson.id == StudentLessonProgress.lesson_id)
            .where(
                StudentLessonProgress.student_id == student.id,
                Lesson.level_number == ln,
                StudentLessonProgress.status == "completed",
            )
        ).scalar() or 0
        by_level.append(
            {
                "level": ln,
                "total": int(total),
                "completed": int(completed),
                "unlocked": True,
            }
        )

    xp_rows = db.execute(
        select(XpTransaction.amount, XpTransaction.created_at)
        .where(XpTransaction.student_id == student.id)
        .order_by(XpTransaction.created_at.desc())
        .limit(14)
    ).all()

    xp_history = []
    day_totals: dict[str, int] = {}
    for amount, created in xp_rows:
        d = created.date().isoformat()
        day_totals[d] = day_totals.get(d, 0) + int(amount)
    for d, xp in sorted(day_totals.items())[-14:]:
        xp_history.append({"date": d, "xp": xp})

    return {
        "by_module": by_module,
        "by_level": by_level,
        "xp_history": xp_history,
        "streak": {
            "current": student.streak_days,
            "best": student.streak_days,
            "last_activity": date.today().isoformat(),
        },
    }
