from app.domain.types import SECIPhase, UserModelSnapshot
from app.services.role_router_service import RoleRouterService


def test_router_respects_mode_override():
    router = RoleRouterService()
    decision = router.route(
        message="Explain this",
        mode_override="ESN",
        retrieval_signals={"retrieval_confidence": 0.9},
        user_model=UserModelSnapshot(user_id="u1"),
        session_phase=SECIPhase.COMBINATION,
    )
    assert decision.mode_distance.value == "ESN"
    assert decision.confidence >= 0.95


def test_router_infers_swp_for_status_intent():
    router = RoleRouterService()
    decision = router.route(
        message="Bring mich auf Stand mit Entscheidungen und ToDos",
        mode_override=None,
        retrieval_signals={"retrieval_confidence": 0.5},
        user_model=UserModelSnapshot(user_id="u1"),
        session_phase=SECIPhase.COMBINATION,
    )
    assert decision.mode_distance.value == "SWP"
    assert decision.output_schema_id == "swp_v1"
    assert decision.retrieval_policy["k"] >= 8


def test_router_infers_skm_for_pattern_intent():
    router = RoleRouterService()
    decision = router.route(
        message="Find patterns, outliers and hypotheses across docs",
        mode_override="AUTO",
        retrieval_signals={"retrieval_confidence": 0.4},
        user_model=UserModelSnapshot(user_id="u1"),
        session_phase=SECIPhase.COMBINATION,
    )
    assert decision.mode_distance.value == "SKM"
    assert decision.retrieval_policy["mmr"] is True


def test_router_asks_clarifying_questions_when_confidence_low():
    router = RoleRouterService()
    decision = router.route(
        message="Kannst du helfen?",
        mode_override="AUTO",
        retrieval_signals={"retrieval_confidence": 0.5},
        user_model=UserModelSnapshot(user_id="u1"),
        session_phase=SECIPhase.COMBINATION,
    )
    assert decision.confidence < 0.7
    assert decision.switch_suggestion is not None
    assert decision.clarification_questions
