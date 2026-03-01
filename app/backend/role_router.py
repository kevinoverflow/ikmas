from __future__ import annotations

ROLE_DIGITAL_MEMORY = "DigitalMemoryAgent"
ROLE_MENTOR = "MentorAgent"
ROLE_TUTOR = "TutoringAgent"
ROLE_CONCEPT_MINING = "ConceptMiningAgent"


def _answer(v):
    if isinstance(v, list):
        return (v[0] if v else "") or ""
    return v or ""


def _route_from_gate(role_gate_answers: dict) -> str | None:
    if not role_gate_answers:
        return None

    goal = str(_answer(role_gate_answers.get("rg_goal"))).strip().lower()
    mode = str(_answer(role_gate_answers.get("rg_mode"))).strip().lower()

    if mode == "tutoring":
        return ROLE_TUTOR
    if goal == "musteranalyse":
        return ROLE_CONCEPT_MINING
    if mode == "dokumentieren" or goal == "projektkontext":
        return ROLE_DIGITAL_MEMORY
    if goal in {"verstehen", "vergleich"} or mode == "erklaeren":
        return ROLE_MENTOR
    return None


def route_role(
    intent: str,
    distance: str,
    retrieval_confidence: float,
    user_profile: dict,
    session_ctx: dict,
    role_gate_answers: dict | None = None,
) -> str:
    gate_role = _route_from_gate(role_gate_answers or {})
    if gate_role:
        return gate_role

    if intent == "learn_mode" or bool(session_ctx.get("force_tutor_mode")):
        return ROLE_TUTOR

    if distance == "SKM" or intent == "pattern_mining":
        return ROLE_CONCEPT_MINING

    if distance == "ESN" or intent in {"what_is", "simplify"}:
        return ROLE_MENTOR

    if distance == "SWPr" or intent == "cross_context":
        return ROLE_DIGITAL_MEMORY

    if retrieval_confidence < 0.55 and user_profile.get("role") == "novice":
        return ROLE_TUTOR

    return ROLE_DIGITAL_MEMORY
