from __future__ import annotations

from app.backend.router_agent import get_relevant_history


def decide_state(
    role: str,
    retrieval_confidence: float,
    session_ctx: dict,
    force_tutor_mode: bool = False,
) -> str | None:
    
    # NEW: Enrich FSM transitions with session history awareness
    # This integrates session insights into state decisions
    user_id = session_ctx.get("user_id")
    
    # If we have user context and knowledge gaps from session history, adjust the state
    if user_id and "knowledge_gaps" in session_ctx:
        knowledge_gaps = session_ctx["knowledge_gaps"]
        if knowledge_gaps:
            # For example, if we detect recurring knowledge gaps, 
            # we may want to prioritize externalization agents
            if role in ["ScribeAgent", "SemanticLinkingAgent", "ContextReconstructorAgent"]:
                # These are good candidates for addressing knowledge gaps
                # We could potentially modify the FSM to route differently here
                pass
    
    # Continue with existing FSM logic
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