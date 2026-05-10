import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager

from fastapi.testclient import TestClient

from app.deps import get_current_student
from app.main import app
from app.models import Student

client = TestClient(app)


def _student(profile: str = "analytics", current_level: str = "level_2") -> Student:
    return Student(
        id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        auth_user_id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
        name="Test Student",
        email="test@example.com",
        profile=profile,
        current_level=current_level,
        total_xp=0,
        streak_days=0,
        diagnostic_status="completed",
        onboarding_done=True,
    )


@contextmanager
def _override_student(factory: Callable[[], Student]) -> Iterator[None]:
    app.dependency_overrides[get_current_student] = factory
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_current_student, None)


def test_lesson_modes_endpoint_returns_selectable_modes() -> None:
    with _override_student(lambda: _student()):
        response = client.get("/lessons/sql-motor-analise/modes")

    assert response.status_code == 200
    modes = response.json()["modes"]
    mode_keys = {mode["mode"] for mode in modes}
    assert {"moment_gated", "socratic", "inner_monologue"}.issubset(mode_keys)


def test_recommend_mode_endpoint_returns_authenticated_recommendation() -> None:
    with _override_student(lambda: _student(profile="strategy", current_level="level_3")):
        response = client.post("/lessons/sql-motor-analise/recommend-mode")

    assert response.status_code == 200
    assert response.json()["recommended_mode"] == "socratic"
    assert response.json()["reason"]
