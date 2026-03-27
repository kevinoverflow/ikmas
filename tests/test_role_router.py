import pytest

from app.backend.role_router import role_router


def test_role_router_forces_tutoring_agent_for_learn_mode():
    role = role_router(
        intent="learn_mode",
        distance="SWPr",
        session_ctx={},
    )

    assert role == "TutoringAgent"


def test_role_router_forces_tutoring_agent_from_session_context():
    role = role_router(
        intent="cross_context",
        distance="SWPr",
        session_ctx={"force_tutor_mode": True},
    )

    assert role == "TutoringAgent"


@pytest.mark.parametrize(
    ("intent", "distance", "expected"),
    [
        ("project_specific", "SWP", "DigitalMemoryAgent"),
        ("pattern_mining", "SKM", "ConceptMiningAgent"),
        ("what_is", "ESN", "MentorAgent"),
        ("simplify", "ESN", "MentorAgent"),
        ("project_specific", "ESN", "TutoringAgent"),
        ("cross_context", "SWPr", "MentorAgent"),
        ("project_specific", "UNKNOWN", "MentorAgent"),
    ],
)
def test_role_router_routes_each_distance_branch(intent, distance, expected):
    role = role_router(
        intent=intent,
        distance=distance,
        session_ctx={},
    )

    assert role == expected
