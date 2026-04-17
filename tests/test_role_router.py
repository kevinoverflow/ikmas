import pytest

from app.backend.role_router import role_router


def test_role_router_returns_mentor_agent_for_learn_mode():
    role = role_router(
        intent="learn_mode",
        distance="SWPr",
        knowledge_mode="SOCIALIZATION",
        session_ctx={},
    )

    assert role == "MentorAgent"


def test_role_router_ignores_legacy_force_tutor_flag():
    role = role_router(
        intent="cross_context",
        distance="SWPr",
        knowledge_mode="SOCIALIZATION",
        session_ctx={"force_tutor_mode": True},
    )

    assert role == "MentorAgent"


@pytest.mark.parametrize(
    ("intent", "distance", "knowledge_mode", "expected"),
    [
        ("project_specific", "SWP", "EXTERNALIZATION", "ScribeAgent"),
        ("project_specific", "SWP", "COMBINATION", "SemanticLinkingAgent"),
        ("project_specific", "SWP", "INTERNALIZATION", "MentorAgent"),
        ("project_specific", "SWP", "SOCIALIZATION", "MentorAgent"),
        ("what_is", "ESN", "SOCIALIZATION", "MentorAgent"),
        ("project_specific", "ESN", "EXTERNALIZATION", "MentorAgent"),
        ("simplify", "ESN", "COMBINATION", "MentorAgent"),
        ("project_specific", "ESN", "INTERNALIZATION", "MentorAgent"),
        ("cross_context", "SKM", "SOCIALIZATION", "MentorAgent"),
        ("cross_context", "SKM", "EXTERNALIZATION", "MentorAgent"),
        ("pattern_mining", "SKM", "COMBINATION", "ContextReconstructorAgent"),
        ("pattern_mining", "SKM", "INTERNALIZATION", "ContextReconstructorAgent"),
        ("project_specific", "UNKNOWN", "SOCIALIZATION", "MentorAgent"),
    ],
)
def test_role_router_routes_each_distance_branch(intent, distance, knowledge_mode, expected):
    role = role_router(
        intent=intent,
        distance=distance,
        knowledge_mode=knowledge_mode,
        session_ctx={},
    )

    assert role == expected
