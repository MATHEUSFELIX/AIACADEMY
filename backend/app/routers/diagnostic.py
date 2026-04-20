"""Diagnostic conversational flow."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_student
from app.memory.redis_cache import rate_limit_check
from app.models import DiagnosticSession, Student
from app.services.brainagent_service import (
    diagnostic_opening_message,
    diagnostic_turn,
)

router = APIRouter()


class AnswerIn(BaseModel):
    session_id: UUID
    answer: str = Field(..., min_length=1)


@router.post("/start")
def diagnostic_start(
    db: Annotated[Session, Depends(get_db)],
    student: Annotated[Student, Depends(get_current_student)],
) -> dict:
    if student.diagnostic_status == "completed":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Diagnostic already completed")

    rate_limit_check(student.id, "diagnostic", 60)

    msg = diagnostic_opening_message()
    conv = [{"role": "assistant", "content": msg, "block": "A"}]
    sess = DiagnosticSession(
        student_id=student.id,
        status="in_progress",
        conversation=conv,
    )
    db.add(sess)
    student.diagnostic_status = "in_progress"
    db.commit()
    db.refresh(sess)

    return {
        "session_id": str(sess.id),
        "message": msg,
        "block": "A",
        "question_number": 1,
        "total_questions_estimate": "10-15",
    }


@router.post("/answer")
def diagnostic_answer(
    body: AnswerIn,
    db: Annotated[Session, Depends(get_db)],
    student: Annotated[Student, Depends(get_current_student)],
) -> dict:
    rate_limit_check(student.id, "diagnostic", 60)

    sess = db.get(DiagnosticSession, body.session_id)
    if not sess or sess.student_id != student.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if sess.status == "completed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Session already completed")

    conv = list(sess.conversation or [])
    conv.append({"role": "user", "content": body.answer})

    summary = "\n".join(f"{m.get('role','?')}: {m.get('content','')}" for m in conv[-12:])
    last_block = conv[-2].get("block", "A") if len(conv) >= 2 else "A"

    msg, meta = diagnostic_turn(summary, body.answer, last_block)
    conv.append({"role": "assistant", "content": msg, "block": meta.get("next_block", "A")})
    sess.conversation = conv

    if meta.get("block_completed"):
        blk = meta.get("next_block", "A")
        if blk in ("B", "C", "D", "done"):
            if last_block == "A" or meta.get("next_block") == "B":
                sess.block_a_completed = True
        # Simplified block flags
        if meta.get("next_block") == "B":
            sess.block_a_completed = True
        if meta.get("next_block") == "C":
            sess.block_b_completed = True
        if meta.get("next_block") == "D":
            sess.block_c_completed = True

    if meta.get("done"):
        from datetime import datetime, timezone

        lvl = meta.get("identified_level") or "level_1"
        sess.status = "completed"
        sess.completed_at = datetime.now(timezone.utc)
        sess.identified_level = lvl
        student.diagnostic_status = "completed"
        student.current_level = lvl
        student.brainagent_notes = msg[:2000]
        db.commit()
        return {
            "type": "completed",
            "identified_level": lvl,
            "message": msg,
            "summary": msg[:400],
            "recommended_path": {
                "start_lesson": "sql-motor-analise",
                "total_lessons": 47,
                "estimated_hours": 85,
            },
        }

    db.commit()
    return {
        "type": "question",
        "message": msg,
        "block": meta.get("next_block", "A"),
        "question_number": sum(1 for m in conv if m.get("role") == "assistant"),
    }


@router.get("/status")
def diagnostic_status(
    db: Annotated[Session, Depends(get_db)],
    student: Annotated[Student, Depends(get_current_student)],
) -> dict:
    if student.diagnostic_status != "completed":
        return {"status": student.diagnostic_status or "not_started"}
    last = db.execute(
        select(DiagnosticSession)
        .where(
            DiagnosticSession.student_id == student.id,
            DiagnosticSession.status == "completed",
        )
        .order_by(DiagnosticSession.completed_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    completed_at = last.completed_at.isoformat() if last and last.completed_at else None
    return {
        "status": "completed",
        "identified_level": student.current_level,
        "completed_at": completed_at,
    }
