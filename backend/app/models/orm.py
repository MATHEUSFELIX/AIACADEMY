"""SQLAlchemy ORM models — column names align with docs/schema.sql."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, ForeignKey, Integer, Numeric, SmallInteger, String, Text, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Student(Base):
    __tablename__ = "students"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    auth_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    profile: Mapped[str | None] = mapped_column(String(32))
    current_level: Mapped[str] = mapped_column(String(32), server_default=text("'level_0'"))
    total_xp: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    streak_days: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    last_activity_at: Mapped[datetime | None] = mapped_column(nullable=True)
    diagnostic_status: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default=text("'not_started'")
    )
    onboarding_done: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("NOW()"))

    lesson_progress: Mapped[list[StudentLessonProgress]] = relationship(
        "StudentLessonProgress", back_populates="student"
    )


class Lesson(Base):
    __tablename__ = "lessons"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    subtitle: Mapped[str | None] = mapped_column(String(300))
    module: Mapped[str] = mapped_column(String(16), nullable=False)
    level_number: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    order_in_level: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("1"))
    xp_reward: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("100"))
    duration_min: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("30"))
    hook_config: Mapped[dict] = mapped_column(JSONB, nullable=False)
    widget_config: Mapped[dict] = mapped_column(JSONB, nullable=False)
    kb_content: Mapped[dict] = mapped_column(JSONB, nullable=False)
    exercise_base: Mapped[dict] = mapped_column(JSONB, nullable=False)
    prerequisites: Mapped[list[str]] = mapped_column(ARRAY(String(80)), nullable=False, server_default=text("'{}'"))
    connections: Mapped[list[str]] = mapped_column(ARRAY(String(80)), nullable=False, server_default=text("'{}'"))
    kb_confidence: Mapped[float] = mapped_column(Numeric(3, 2), nullable=False, server_default=text("0.90"))
    kb_entropy: Mapped[float] = mapped_column(Numeric(4, 2), nullable=False, server_default=text("5.0"))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("NOW()"))


class StudentLessonProgress(Base):
    __tablename__ = "student_lesson_progress"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )
    lesson_id: Mapped[str] = mapped_column(String(80), ForeignKey("lessons.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default=text("'locked'"))

    score_technical: Mapped[float | None] = mapped_column(Numeric(3, 2))
    score_methodological: Mapped[float | None] = mapped_column(Numeric(3, 2))
    score_antipatterns: Mapped[float | None] = mapped_column(Numeric(3, 2))
    score_interpretation: Mapped[float | None] = mapped_column(Numeric(3, 2))
    score_composite: Mapped[float | None] = mapped_column(Numeric(3, 2))

    variant_used: Mapped[str | None] = mapped_column(String(32))
    used_hint: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    xp_earned: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("0"))
    attempts: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("0"))

    confidence_before: Mapped[float | None] = mapped_column(Numeric(3, 2))
    confidence_after: Mapped[float | None] = mapped_column(Numeric(3, 2))

    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("NOW()"))

    student: Mapped[Student] = relationship("Student", back_populates="lesson_progress")
    lesson: Mapped[Lesson] = relationship("Lesson")


class EpisodicMemory(Base):
    __tablename__ = "episodic_memory"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )
    lesson_id: Mapped[str | None] = mapped_column(String(80), ForeignKey("lessons.id"))
    context: Mapped[str] = mapped_column(Text, nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    outcome: Mapped[str | None] = mapped_column(Text)
    valence: Mapped[float] = mapped_column(Numeric(3, 2), nullable=False, server_default=text("0.5"))
    importance: Mapped[float] = mapped_column(Numeric(3, 2), nullable=False, server_default=text("0.5"))
    entropy: Mapped[float | None] = mapped_column(Numeric(4, 2))
    created_at: Mapped[datetime] = mapped_column(server_default=text("NOW()"))


class ProceduralMemory(Base):
    __tablename__ = "procedural_memory"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )
    pattern: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence: Mapped[float] = mapped_column(Numeric(3, 2), nullable=False, server_default=text("0.5"))
    evidence_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    created_at: Mapped[datetime] = mapped_column(server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("NOW()"))


class DiagnosticSession(Base):
    __tablename__ = "diagnostic_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default=text("'in_progress'"))

    block_a_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    block_b_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    block_c_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    block_d_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))

    identified_level: Mapped[str | None] = mapped_column(String(32))
    brainagent_notes: Mapped[str | None] = mapped_column(Text)
    conversation: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))

    started_at: Mapped[datetime] = mapped_column(server_default=text("NOW()"))
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=text("NOW()"))


class ExerciseSubmission(Base):
    __tablename__ = "exercise_submissions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )
    lesson_id: Mapped[str] = mapped_column(String(80), ForeignKey("lessons.id"), nullable=False)
    attempt_number: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("1"))

    student_answer: Mapped[str] = mapped_column(Text, nullable=False)
    exercise_variant: Mapped[str] = mapped_column(String(32), nullable=False)
    generated_exercise: Mapped[dict] = mapped_column(JSONB, nullable=False)

    score_technical: Mapped[float | None] = mapped_column(Numeric(3, 2))
    score_methodological: Mapped[float | None] = mapped_column(Numeric(3, 2))
    score_antipatterns: Mapped[float | None] = mapped_column(Numeric(3, 2))
    score_interpretation: Mapped[float | None] = mapped_column(Numeric(3, 2))
    score_composite: Mapped[float | None] = mapped_column(Numeric(3, 2))
    brainagent_feedback: Mapped[str | None] = mapped_column(Text)

    used_hint: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    xp_earned: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("0"))
    created_at: Mapped[datetime] = mapped_column(server_default=text("NOW()"))


class StudentObjective(Base):
    __tablename__ = "student_objectives"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("1"))
    progress: Mapped[float] = mapped_column(Numeric(3, 2), nullable=False, server_default=text("0.0"))
    deadline: Mapped[date | None] = mapped_column(nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("NOW()"))


class XpTransaction(Base):
    __tablename__ = "xp_transactions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )
    amount: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    reason: Mapped[str] = mapped_column(String(100), nullable=False)
    lesson_id: Mapped[str | None] = mapped_column(String(80), ForeignKey("lessons.id"))
    created_at: Mapped[datetime] = mapped_column(server_default=text("NOW()"))
