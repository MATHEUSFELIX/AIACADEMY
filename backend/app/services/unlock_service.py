"""Recompute lesson availability from prerequisites and completion scores."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Lesson, Student, StudentLessonProgress
from app.services.student_service import ensure_all_lesson_progress

logger = logging.getLogger(__name__)

SCORE_THRESHOLD = 0.75


def _prereqs_met(
    db: Session, student_id: uuid.UUID, lesson: Lesson
) -> bool:
    for pid in lesson.prerequisites or []:
        row = db.execute(
            select(StudentLessonProgress).where(
                StudentLessonProgress.student_id == student_id,
                StudentLessonProgress.lesson_id == pid,
            )
        ).scalar_one_or_none()
        if not row or row.score_composite is None:
            return False
        if float(row.score_composite) < SCORE_THRESHOLD:
            return False
    return True


def refresh_unlocks_for_student(db: Session, student_id: uuid.UUID) -> int:
    """Set 'available' for lessons whose prereqs are satisfied. Returns count changed."""
    ensure_all_lesson_progress(db, student_id)
    lessons = db.execute(select(Lesson).where(Lesson.is_active == True)).scalars().all()  # noqa: E712
    changed = 0
    for lesson in lessons:
        slp = db.execute(
            select(StudentLessonProgress).where(
                StudentLessonProgress.student_id == student_id,
                StudentLessonProgress.lesson_id == lesson.id,
            )
        ).scalar_one_or_none()
        if not slp or slp.status == "completed":
            continue
        if slp.status == "locked" and _prereqs_met(db, student_id, lesson):
            slp.status = "available"
            changed += 1
    db.commit()
    return changed


def lesson_is_accessible(db: Session, student_id: uuid.UUID, lesson_id: str) -> bool:
    slp = db.execute(
        select(StudentLessonProgress).where(
            StudentLessonProgress.student_id == student_id,
            StudentLessonProgress.lesson_id == lesson_id,
        )
    ).scalar_one_or_none()
    if not slp:
        return False
    if slp.status == "locked":
        lesson = db.get(Lesson, lesson_id)
        if lesson and _prereqs_met(db, student_id, lesson):
            return True
        return False
    return True


def maybe_advance_level(db: Session, student: Student) -> None:
    """Advance current_level when 80% of lessons at current level have score >= threshold."""
    lvl = student.current_level or "level_0"
    num = int(lvl.split("_")[1])
    lessons = db.execute(
        select(Lesson).where(Lesson.level_number == num, Lesson.is_active == True)  # noqa: E712
    ).scalars().all()
    if not lessons:
        return
    done = 0
    for lesson in lessons:
        slp = db.execute(
            select(StudentLessonProgress).where(
                StudentLessonProgress.student_id == student.id,
                StudentLessonProgress.lesson_id == lesson.id,
                StudentLessonProgress.status == "completed",
            )
        ).scalar_one_or_none()
        if not slp:
            continue
        if slp.score_composite is not None and float(slp.score_composite) >= SCORE_THRESHOLD:
            done += 1
    ratio = done / len(lessons)
    if ratio >= 0.80 and num < 10:
        student.current_level = f"level_{num + 1}"
        db.commit()
        logger.info("Student %s advanced to %s", student.id, student.current_level)
