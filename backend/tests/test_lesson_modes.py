from uuid import uuid4

from app.main import app
from app.routers.lessons import ExerciseSubmitIn, LESSON_MODES, _mode_result_for


def test_lesson_mode_routes_are_registered() -> None:
    paths = {route.path for route in app.routes}

    assert "/lessons/{lesson_id}/modes" in paths
    assert "/lessons/{lesson_id}/recommend-mode" in paths


def test_lesson_modes_match_frontend_contract() -> None:
    assert LESSON_MODES
    for mode in LESSON_MODES:
        assert set(mode) == {"mode", "name", "description", "emoji", "icon"}
        assert mode["mode"]
        assert mode["name"]
        assert mode["description"]


def test_exercise_submit_accepts_brainagent_mode() -> None:
    body = ExerciseSubmitIn(
        exercise_id=uuid4(),
        answer="Minha resposta",
        used_hint=False,
        brainagent_mode="competitive",
    )

    assert body.brainagent_mode == "competitive"


def test_mode_result_matches_frontend_expected_fields() -> None:
    competitive = _mode_result_for("competitive", 0.82)
    socratic = _mode_result_for("socratic", 0.6)
    progressive = _mode_result_for("progressive", 0.8)

    assert {"winner", "student_score", "agent_score"} <= set(competitive)
    assert "next_question" in socratic
    assert "next_unlocked_modes" in progressive
