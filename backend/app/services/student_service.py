"""Student lifecycle — ensure row exists and initialize lesson progress."""

from __future__ import annotations

import logging
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Lesson, Student, StudentLessonProgress, XpTransaction

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


def ensure_all_lesson_progress(db: Session, student_id: uuid.UUID) -> None:
    """Garante uma linha de progresso por aula ativa (ex.: após novo seed). Desbloqueia nível 0 inicial."""
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


def touch_activity(db: Session, student: Student) -> None:
    """Update last_activity_at and recompute streak_days."""
    now = datetime.now(timezone.utc)
    today: date = now.date()

    last = student.last_activity_at
    if last is not None:
        last_date = last.date() if isinstance(last, datetime) else last
        days_since = (today - last_date).days
        if days_since == 0:
            # Already counted today — no change to streak
            pass
        elif days_since == 1:
            # Consecutive day — extend streak
            student.streak_days = (student.streak_days or 0) + 1
            _grant_streak_xp(db, student)
        else:
            # Gap > 1 day — reset streak
            student.streak_days = 1
    else:
        student.streak_days = 1

    student.last_activity_at = now
    db.commit()


def _grant_streak_xp(db: Session, student: Student) -> None:
    """Grant +50 XP per day after a 7-day streak is reached."""
    streak = student.streak_days or 0
    if streak >= 7:
        student.total_xp = (student.total_xp or 0) + 50
        db.add(
            XpTransaction(
                student_id=student.id,
                amount=50,
                reason=f"streak_{streak}_days",
            )
        )
