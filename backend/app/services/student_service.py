"""Student lifecycle — ensure row exists and initialize lesson progress."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Lesson, Student, StudentLessonProgress

logger = logging.getLogger(__name__)


def ensure_student(
    db: Session,
    *,
    auth_user_id: uuid.UUID,
    email: str,
    default_name: str,
) -> Student:
    existing = db.execute(
        select(Student).where(Student.auth_user_id == auth_user_id)
    ).scalar_one_or_none()
    if existing:
        if existing.email != email:
            existing.email = email
            db.commit()
            db.refresh(existing)
        return existing

    st = Student(
        auth_user_id=auth_user_id,
        email=email,
        name=default_name[:150],
    )
    db.add(st)
    db.commit()
    db.refresh(st)
    initialize_progress_for_student(db, st.id)
    logger.info("Created student %s", st.id)
    return st


def initialize_progress_for_student(db: Session, student_id: uuid.UUID) -> None:
    """Insert locked progress for every active lesson."""
    lesson_ids = db.execute(select(Lesson.id).where(Lesson.is_active == True)).scalars().all()  # noqa: E712
    for lid in lesson_ids:
        exists = db.execute(
            select(StudentLessonProgress.id).where(
                StudentLessonProgress.student_id == student_id,
                StudentLessonProgress.lesson_id == lid,
            )
        ).first()
        if exists:
            continue
        db.add(
            StudentLessonProgress(
                student_id=student_id,
                lesson_id=lid,
                status="locked",
            )
        )
    db.commit()
    unlock_starting_lessons(db, student_id)


def unlock_starting_lessons(db: Session, student_id: uuid.UUID) -> None:
    """Make level-0 first lessons and zero-prerequisite lessons available."""
    rows = db.execute(
        select(Lesson).where(Lesson.is_active == True)  # noqa: E712
    ).scalars().all()
    for lesson in rows:
        pre = lesson.prerequisites or []
        if len(pre) == 0 and lesson.level_number == 0:
            slp = db.execute(
                select(StudentLessonProgress).where(
                    StudentLessonProgress.student_id == student_id,
                    StudentLessonProgress.lesson_id == lesson.id,
                )
            ).scalar_one_or_none()
            if slp and slp.status == "locked":
                slp.status = "available"
    db.commit()


def touch_activity(db: Session, student: Student) -> None:
    student.last_activity_at = datetime.utcnow()
    db.commit()
