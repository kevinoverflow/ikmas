from app.backend.role_gate import (
    infer_intent_distance_from_gate_answers,
    infer_role_from_gate_answers,
    parse_role_gate_answers,
    role_gate_payload,
    should_open_role_gate,
)


def test_parse_role_gate_answers_json():
    answers = parse_role_gate_answers('{"role_gate_answers": {"rg_goal": "verstehen"}}')
    assert answers == {"rg_goal": "verstehen"}


def test_parse_role_gate_answers_non_json_returns_none():
    assert parse_role_gate_answers("hello") is None


def test_infer_role_from_answers_mapping():
    assert infer_role_from_gate_answers({"rg_goal": "verstehen", "rg_mode": "erklaeren"}) == "MentorAgent"
    assert infer_role_from_gate_answers({"rg_goal": "verstehen", "rg_mode": "tutoring"}) == "TutoringAgent"
    assert infer_role_from_gate_answers({"rg_goal": "projektkontext", "rg_mode": "dokumentieren"}) == "DigitalMemoryAgent"
    assert infer_role_from_gate_answers({"rg_goal": "musteranalyse", "rg_mode": "erklaeren"}) == "ConceptMiningAgent"


def test_infer_intent_distance_from_answers_mapping():
    assert infer_intent_distance_from_gate_answers({"rg_goal": "verstehen", "rg_mode": "erklaeren"}) == ("what_is", "ESN")
    assert infer_intent_distance_from_gate_answers({"rg_goal": "vergleich", "rg_mode": "erklaeren"}) == ("cross_context", "SWPr")


def test_should_open_role_gate_defaults():
    assert should_open_role_gate("project_specific", {}, None, None) is True
    assert should_open_role_gate("what_is", {}, None, None) is False
    assert should_open_role_gate("project_specific", {}, "MentorAgent", None) is False


def test_role_gate_payload_contract():
    payload = role_gate_payload()
    assert payload["mode"] == "role_clarification"
    assert payload["interaction_phase"] == "ROLE_GATE"
    assert len(payload["questions"]) == 2
