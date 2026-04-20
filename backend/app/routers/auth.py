"""Onboarding — requires authenticated Supabase user."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_student
from app.models import Student

router = APIRouter()


class OnboardingIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    profile: str = Field(..., pattern="^(analytics|marketing|strategy|c_level|produto)$")


@router.post("/onboarding")
def complete_onboarding(
    body: OnboardingIn,
    db: Annotated[Session, Depends(get_db)],
    student: Annotated[Student, Depends(get_current_student)],
) -> dict:
    if student.onboarding_done:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Onboarding already completed",
        )
    student.name = body.name[:150]
    student.profile = body.profile
    student.onboarding_done = True
    db.commit()
    return {
        "student_id": str(student.id),
        "name": student.name,
        "profile": body.profile,
        "onboarding_done": True,
        "next_step": "diagnostic",
    }
