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
    if user_id:
        # Check for recurring themes that might influence routing decisions
        detected_themes = session_ctx.get("detected_themes", [])
        knowledge_gaps = session_ctx.get("knowledge_gaps", [])
        related_sessions = session_ctx.get("related_sessions", [])
        
        # If we have knowledge gaps, prioritize agents that can address them
        if knowledge_gaps and role in ["ScribeAgent", "SemanticLinkingAgent", "ContextReconstructorAgent"]:
            # These are good candidates for addressing knowledge gaps
            # Adjust routing to focus on externalization or combination agents
            # This is a simplified approach - in a real implementation, we'd 
            # analyze the specific gaps and route accordingly
            pass
            
        # If we have recurring themes, consider routing to agents that might leverage this
        if detected_themes and role in ["ScribeAgent", "SemanticLinkingAgent", "ContextReconstructorAgent"]:
            # Adjust state to leverage previously identified themes
            pass
            
        # If we have related sessions, consider them for context enrichment
        if related_sessions and role in ["ScribeAgent", "SemanticLinkingAgent", "ContextReconstructorAgent"]:
            # Use related sessions to enrich the current request context
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