from app.backend.role_router import route_role


def test_router_learn_mode_forces_tutoring():
    role = route_role(
        intent="learn_mode",
        distance="SWP",
        retrieval_confidence=0.9,
        user_profile={"role": "member"},
        session_ctx={},
    )
    assert role == "TutoringAgent"


def test_router_pattern_mining_routes_concept_mining():
    role = route_role(
        intent="pattern_mining",
        distance="SKM",
        retrieval_confidence=0.9,
        user_profile={"role": "member"},
        session_ctx={},
    )
    assert role == "ConceptMiningAgent"


def test_router_esn_routes_mentor():
    role = route_role(
        intent="what_is",
        distance="ESN",
        retrieval_confidence=0.9,
        user_profile={"role": "member"},
        session_ctx={},
    )
    assert role == "MentorAgent"


def test_router_gate_answers_have_priority():
    role = route_role(
        intent="what_is",
        distance="ESN",
        retrieval_confidence=0.9,
        user_profile={"role": "member"},
        session_ctx={},
        role_gate_answers={"rg_goal": "musteranalyse", "rg_mode": "erklaeren"},
    )
    assert role == "ConceptMiningAgent"
