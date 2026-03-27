import pytest

from app.backend.fsm import decide_state


def test_decide_state_returns_none_for_non_tutoring_roles_by_default():
    state = decide_state(
        role="MentorAgent",
        retrieval_confidence=0.9,
        session_ctx={},
    )

    assert state is None


def test_decide_state_can_force_tutor_mode_for_other_roles():
    state = decide_state(
        role="MentorAgent",
        retrieval_confidence=0.9,
        session_ctx={},
        force_tutor_mode=True,
    )

    assert state == "EXPLAIN"


@pytest.mark.parametrize(
    ("retrieval_confidence", "expected"),
    [
        (0.75, "EXPLAIN"),
        (0.2, "ASSESS"),
    ],
)
def test_decide_state_chooses_initial_state_from_confidence(retrieval_confidence, expected):
    state = decide_state(
        role="TutoringAgent",
        retrieval_confidence=retrieval_confidence,
        session_ctx={},
    )

    assert state == expected


@pytest.mark.parametrize(
    ("session_ctx", "expected"),
    [
        ({"state": "ASSESS"}, "EXPLAIN"),
        ({"state": "EXPLAIN"}, "CHECK"),
        ({"state": "CHECK", "answered_check": False}, "CHECK"),
        ({"state": "CHECK", "answered_check": True}, "PRACTICE"),
        ({"state": "PRACTICE", "practice_done": False}, "PRACTICE"),
        ({"state": "PRACTICE", "practice_done": True}, "FEEDBACK"),
        ({"state": "FEEDBACK"}, "SCHEDULE"),
        ({"state": "SCHEDULE"}, "ASSESS"),
        ({"state": "UNKNOWN"}, "ASSESS"),
    ],
)
def test_decide_state_transitions_as_expected(session_ctx, expected):
    state = decide_state(
        role="TutoringAgent",
        retrieval_confidence=0.5,
        session_ctx=session_ctx,
    )

    assert state == expected
