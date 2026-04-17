from __future__ import annotations

from app.domain.types import Distance, Intent, KnowledgeMode, RoleName

ROLE_MATRIX: dict[tuple[Distance, KnowledgeMode], RoleName] = {
    ("SWP", "EXTERNALIZATION"): "ScribeAgent",
    ("SWP", "COMBINATION"): "SemanticLinkingAgent",
    ("ESN", "SOCIALIZATION"): "MentorAgent",
    ("ESN", "INTERNALIZATION"): "MentorAgent",
    ("SKM", "COMBINATION"): "ContextReconstructorAgent",
    ("SKM", "INTERNALIZATION"): "ContextReconstructorAgent",
}

def role_router(
        intent: Intent,
        distance: Distance,
        knowledge_mode: KnowledgeMode,
        session_ctx: dict,
) -> RoleName:
    return ROLE_MATRIX.get((distance, knowledge_mode), "MentorAgent")
