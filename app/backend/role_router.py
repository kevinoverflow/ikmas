from __future__ import annotations
from app.domain.types import Distance, Intent, RoleName

def role_router(
        intent: Intent,
        distance: Distance,
        session_ctx: dict,
) -> RoleName:
    force_tutor = bool(session_ctx.get("force_tutor_mode")) or intent == "learn_mode"

    if force_tutor:
        return "TutoringAgent"

    if distance == "SWP":
        return "DigitalMemoryAgent"
    if distance == "SKM":
        return "ConceptMiningAgent"
    if distance == "ESN":
        if intent in {"simplify", "what_is"}:
            return "MentorAgent"
        return "TutoringAgent"
    if distance == "SWPr":
        return "MentorAgent"

    return "MentorAgent"
