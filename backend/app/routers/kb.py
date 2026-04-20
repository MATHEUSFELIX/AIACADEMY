"""Knowledge base concepts listing and detail."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_student
from app.models import Lesson, Student, StudentLessonProgress

router = APIRouter()


def _lesson_to_concept(
    lesson: Lesson,
    prog: StudentLessonProgress | None,
) -> dict:
    status = "locked"
    if prog:
        if prog.status == "completed":
            status = "done"
        elif prog.status == "locked":
            status = "locked"
        elif prog.score_composite is None:
            status = "gap"
        else:
            status = "progress"
    score = float(prog.score_composite) if prog and prog.score_composite else None
    return {
        "id": lesson.id,
        "topic": lesson.title,
        "module": lesson.module,
        "confidence": float(lesson.kb_confidence),
        "entropy": float(lesson.kb_entropy),
        "status": status,
        "connections": list(lesson.connections or []),
        "lesson_id": lesson.id,
        "student_score": score,
    }


@router.get("/concepts")
def list_concepts(
    db: Annotated[Session, Depends(get_db)],
    student: Annotated[Student, Depends(get_current_student)],
    module: str | None = None,
    status_filter: str | None = Query(None, alias="status"),
) -> dict:
    q = select(Lesson).where(Lesson.is_active == True)  # noqa: E712
    if module:
        q = q.where(Lesson.module == module)

    lessons = db.execute(q.order_by(Lesson.level_number)).scalars().all()
    concepts = []
    stats = {"total": 0, "done": 0, "progress": 0, "gap": 0, "locked": 0}

    for lesson in lessons:
        prog = db.execute(
            select(StudentLessonProgress).where(
                StudentLessonProgress.student_id == student.id,
                StudentLessonProgress.lesson_id == lesson.id,
            )
        ).scalar_one_or_none()
        c = _lesson_to_concept(lesson, prog)
        if status_filter and c["status"] != status_filter:
            continue
        row = {k: v for k, v in c.items() if k != "student_score"}
        concepts.append(row)
        stats["total"] += 1
        st = c["status"]
        if st in stats:
            stats[st] += 1

    return {"concepts": concepts, "stats": stats}


@router.get("/concepts/{concept_id}")
def get_concept(
    concept_id: str,
    db: Annotated[Session, Depends(get_db)],
    student: Annotated[Student, Depends(get_current_student)],
) -> dict:
    lesson = db.get(Lesson, concept_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Concept not found")

    prog = db.execute(
        select(StudentLessonProgress).where(
            StudentLessonProgress.student_id == student.id,
            StudentLessonProgress.lesson_id == concept_id,
        )
    ).scalar_one_or_none()

    kb = lesson.kb_content if isinstance(lesson.kb_content, dict) else {}

    score = float(prog.score_composite) if prog and prog.score_composite else None
    st = _lesson_to_concept(lesson, prog)["status"]

    return {
        "id": lesson.id,
        "topic": lesson.title,
        "module": lesson.module,
        "confidence": float(lesson.kb_confidence),
        "entropy": float(lesson.kb_entropy),
        "resumo": kb.get("resumo", ""),
        "quando_usar": kb.get("quando_usar", []),
        "quando_nao_usar": kb.get("quando_nao_usar", []),
        "formula": kb.get("formula", {}),
        "codigo": kb.get("codigo", ""),
        "antipatterns": kb.get("antipatterns", []),
        "fintech_aplicacao": kb.get("fintech_aplicacao", ""),
        "connections": list(lesson.connections or []),
        "student_status": st,
        "student_score": score,
    }
