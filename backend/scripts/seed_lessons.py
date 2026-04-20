"""Load lesson JSON files from backend/content into PostgreSQL."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import Session, sessionmaker

# Allow running as python -m scripts.seed_lessons from backend/
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.models.orm import Lesson  # noqa: E402


def lesson_from_json(data: dict) -> Lesson:
    return Lesson(
        id=data["id"],
        title=data["title"],
        subtitle=data.get("subtitle"),
        module=data["module"],
        level_number=int(data["level_number"]),
        order_in_level=int(data.get("order_in_level", 1)),
        xp_reward=int(data.get("xp_reward", 100)),
        duration_min=int(data.get("duration_min", 30)),
        hook_config=data["hook_config"],
        widget_config=data["widget_config"],
        kb_content=data["kb_content"],
        exercise_base=data["exercise_base"],
        prerequisites=list(data.get("prerequisites", [])),
        connections=list(data.get("connections", [])),
        kb_confidence=float(data.get("kb_confidence", 0.9)),
        kb_entropy=float(data.get("kb_entropy", 5.0)),
        is_active=True,
    )


def run(session: Session, reset: bool) -> None:
    content_dir = ROOT / "content"
    if not content_dir.is_dir():
        raise SystemExit(f"Missing content directory: {content_dir}")

    paths = sorted(content_dir.rglob("*.json"))
    if not paths:
        raise SystemExit("No JSON files under content/")

    if reset:
        session.execute(delete(Lesson))
        session.commit()

    for path in paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        lid = data["id"]
        existing = session.execute(select(Lesson).where(Lesson.id == lid)).scalar_one_or_none()
        row = lesson_from_json(data)
        if existing:
            for col in [
                "title",
                "subtitle",
                "module",
                "level_number",
                "order_in_level",
                "xp_reward",
                "duration_min",
                "hook_config",
                "widget_config",
                "kb_content",
                "exercise_base",
                "prerequisites",
                "connections",
                "kb_confidence",
                "kb_entropy",
                "is_active",
            ]:
                setattr(existing, col, getattr(row, col))
        else:
            session.add(row)
        print(f"Upsert lesson {lid} ({path.name})")

    session.commit()
    print(f"Done. {len(paths)} files processed.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="Delete all lessons before seed")
    args = parser.parse_args()

    import os

    url = os.environ.get("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL required")

    engine = create_engine(url)
    SessionCls = sessionmaker(bind=engine)
    session = SessionCls()
    try:
        run(session, args.reset)
    finally:
        session.close()


if __name__ == "__main__":
    main()
