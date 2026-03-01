from __future__ import annotations

FSM_STATES = ("ASSESS", "EXPLAIN", "CHECK", "PRACTICE", "FEEDBACK", "SCHEDULE")
_TRANSITIONS = {
    "ASSESS": "EXPLAIN",
    "EXPLAIN": "CHECK",
    "CHECK": "PRACTICE",
    "PRACTICE": "FEEDBACK",
    "FEEDBACK": "SCHEDULE",
    "SCHEDULE": "ASSESS",
}


def decide_state(
    role: str,
    retrieval_confidence: float,
    session_ctx: dict,
    force_tutor_mode: bool = False,
) -> str | None:
    is_tutoring = role == "TutoringAgent" or force_tutor_mode
    if not is_tutoring:
        return None

    last_state = session_ctx.get("last_state")

    if not last_state:
        return "EXPLAIN" if retrieval_confidence >= 0.75 else "ASSESS"

    if last_state not in FSM_STATES:
        return "ASSESS"

    return _TRANSITIONS[last_state]
