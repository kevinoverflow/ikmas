from __future__ import annotations

def decide_state(
    role: str,
    retrieval_confidence: float,
    session_ctx: dict,
    force_tutor_mode: bool = False,
) -> str | None:

    if role != "TutoringAgent" and not force_tutor_mode:
        return None

    current = session_ctx.get("state")
    answered_check = session_ctx.get("answered_check", False)
    practice_done = session_ctx.get("practice_done", False)

    if current is None:
        if retrieval_confidence >= 0.75:
            return "EXPLAIN"
        return "ASSESS"

    if current == "ASSESS":
        return "EXPLAIN"

    if current == "EXPLAIN":
        return "CHECK"

    if current == "CHECK":
        return "PRACTICE" if answered_check else "CHECK"

    if current == "PRACTICE":
        return "FEEDBACK" if practice_done else "PRACTICE"

    if current == "FEEDBACK":
        return "SCHEDULE"

    if current == "SCHEDULE":
        return "ASSESS"

    return "ASSESS"