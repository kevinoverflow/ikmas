from __future__ import annotations

import json
from json import JSONDecodeError
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.schema import RouterPayload
from app.domain.types import Distance, KnowledgeMode, RoleName
from app.infrastructure.config import (
    CONTEXT_RECONSTRUCTOR_MODEL_NAME,
    LLM_MODEL_NAME,
    MENTOR_MODEL_NAME,
    SCRIBE_MODEL_NAME,
    SEMANTIC_LINKING_MODEL_NAME,
)
from app.infrastructure.tracing import traceable
from app.prompts.router_agent_prompt import ROUTER_SYSTEM_PROMPT
from app.backend.sqlite_store import get_conn


AGENT_REGISTRY = [
    {
        "agent": "ScribeAgent",
        "label": "Scribe Agent",
        "seci_modes": ["Externalization"],
        "reuse_situations": ["Shared Work Producer"],
        "core_function": "Converts fragmented work traces into explicit reusable artifacts.",
    },
    {
        "agent": "SemanticLinkingAgent",
        "label": "Semantic Linking Agent",
        "seci_modes": ["Combination"],
        "reuse_situations": ["Shared Work Producer"],
        "core_function": "Links explicit artifacts semantically and synthesizes their relations.",
    },
    {
        "agent": "MentorAgent",
        "label": "Mentor Agent",
        "seci_modes": ["Socialization", "Internalization"],
        "reuse_situations": ["Expertise-Seeking Novice"],
        "core_function": "Explains expert knowledge accessibly and supports understanding.",
    },
    {
        "agent": "ContextReconstructorAgent",
        "label": "Context Reconstructor Agent",
        "seci_modes": ["Combination", "Internalization"],
        "reuse_situations": ["Secondary Knowledge Miner"],
        "core_function": "Restores missing context for reuse in a distant or shifted context.",
    },
]

AGENT_ALIASES: dict[str, RoleName] = {
    "scribeagent": "ScribeAgent",
    "scribe agent": "ScribeAgent",
    "semanticlinkingagent": "SemanticLinkingAgent",
    "semantic linking agent": "SemanticLinkingAgent",
    "mentoragent": "MentorAgent",
    "mentor agent": "MentorAgent",
    "contextreconstructoragent": "ContextReconstructorAgent",
    "context reconstructor agent": "ContextReconstructorAgent",
}

SECI_TO_KNOWLEDGE_MODE: dict[str, KnowledgeMode] = {
    "Socialization": "SOCIALIZATION",
    "Externalization": "EXTERNALIZATION",
    "Combination": "COMBINATION",
    "Internalization": "INTERNALIZATION",
}

SECI_ALIASES: dict[str, str] = {
    "socialization": "Socialization",
    "externalization": "Externalization",
    "combination": "Combination",
    "internalization": "Internalization",
}

REUSE_TO_DISTANCE: dict[str, Distance] = {
    "Shared Work Producer": "SWP",
    "Shared Work Practitioner": "SWPr",
    "Expertise-Seeking Novice": "ESN",
    "Secondary Knowledge Miner": "SKM",
}

REUSE_ALIASES: dict[str, str] = {
    "shared work producer": "Shared Work Producer",
    "shared work practitioner": "Shared Work Practitioner",
    "expertise-seeking novice": "Expertise-Seeking Novice",
    "expertise seeking novice": "Expertise-Seeking Novice",
    "secondary knowledge miner": "Secondary Knowledge Miner",
}


class RouteDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: RoleName
    knowledge_mode: KnowledgeMode
    distance: Distance
    routing_confidence: Literal["high", "medium", "low"]
    reason: str
    required_context: list[str] = Field(default_factory=list)
    verification_need: str = "none"
    next_state: str = "agent_execution"
    used_fallback: bool = False
    model_selection: dict[str, Any] = Field(default_factory=dict)
    detected_themes: list[str] = Field(default_factory=list)
    knowledge_gaps: list[str] = Field(default_factory=list)
    related_sessions: list[dict[str, Any]] = Field(default_factory=list)


def build_router_prompt(
    user_input: str,
    chat_history: list[dict[str, str]] | None = None,
    session_insights: dict[str, Any] | None = None,
) -> str:
    history_lines: list[str] = []
    for turn in (chat_history or [])[-5:]:
        user_turn = turn.get("user", "").strip()
        assistant_turn = turn.get("assistant", "").strip()
        if user_turn:
            history_lines.append(f"User: {user_turn}")
        if assistant_turn:
            history_lines.append(f"Assistant: {assistant_turn}")

    history_block = "\n".join(history_lines) if history_lines else "(no prior conversation)"
    session_insights = session_insights or {}

    return json.dumps(
        {
            "available_agents": AGENT_REGISTRY,
            "user_request": user_input,
            "chat_history": history_block,
            "allowed_values": {
                "seci_mode": ["Socialization", "Externalization", "Combination", "Internalization"],
                "reuse_situation": [
                    "Shared Work Producer",
                    "Shared Work Practitioner",
                    "Expertise-Seeking Novice",
                    "Secondary Knowledge Miner",
                ],
                "selected_agent": [
                    "ScribeAgent",
                    "SemanticLinkingAgent",
                    "MentorAgent",
                    "ContextReconstructorAgent",
                ],
                "routing_confidence": ["high", "medium", "low"],
            },
            "session_context": {
                "recurring_themes": session_insights.get("recurring_themes", []),
                "knowledge_gaps": session_insights.get("uncaptured_themes", []),
                "related_sessions": session_insights.get("related_sessions", []),
                "instruction": (
                    "Use session context only as routing evidence. "
                    "Do not let it override the current request when the current request is explicit."
                ),
            },
            "required_output_fields": [
                "seci_mode",
                "reuse_situation",
                "selected_agent",
                "routing_confidence",
                "reason",
                "required_context",
                "verification_need",
                "next_state",
            ],
        },
        ensure_ascii=False,
        indent=2,
    )


ROLE_MODEL_NAMES: dict[RoleName, str] = {
    "ScribeAgent": SCRIBE_MODEL_NAME,
    "SemanticLinkingAgent": SEMANTIC_LINKING_MODEL_NAME,
    "MentorAgent": MENTOR_MODEL_NAME,
    "ContextReconstructorAgent": CONTEXT_RECONSTRUCTOR_MODEL_NAME,
}

ROLE_MODEL_REASONS: dict[RoleName, str] = {
    "ScribeAgent": "Chosen from SCRIBE_MODEL_NAME because the selected role produces structured documentation artifacts.",
    "SemanticLinkingAgent": "Chosen from SEMANTIC_LINKING_MODEL_NAME because the selected role synthesizes semantic relations across explicit artifacts.",
    "MentorAgent": "Chosen from MENTOR_MODEL_NAME because the selected role explains expert knowledge for a novice audience.",
    "ContextReconstructorAgent": "Chosen from CONTEXT_RECONSTRUCTOR_MODEL_NAME because the selected role reconstructs context and transfer conditions.",
}


def model_selection_for_role(role: RoleName) -> dict[str, Any]:
    return {
        "model_name": ROLE_MODEL_NAMES.get(role, LLM_MODEL_NAME),
        "reason": ROLE_MODEL_REASONS.get(role, "Chosen from LLM_MODEL_NAME because no role-specific model is configured."),
        "temperature": 0.2,
        "thinking_required": False,
        "response_format": {"type": "json_object"},
    }


def _load_json_object(raw: str) -> dict:
    text = raw.strip()
    candidates = [text]

    if "```" in text:
        stripped = text.replace("```json", "```").replace("```JSON", "```")
        candidates.extend(part.strip() for part in stripped.split("```") if part.strip())

    first = text.find("{")
    last = text.rfind("}")
    if first != -1 and last != -1 and first < last:
        candidates.append(text[first:last + 1].strip())

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed

    raise JSONDecodeError("No JSON object found in router output.", text, 0)


def _normalize_router_payload(parsed: dict) -> RouterPayload:
    normalized = dict(parsed)

    selected_agent = normalized.get("selected_agent")
    if isinstance(selected_agent, str):
        alias = AGENT_ALIASES.get(selected_agent.strip().lower())
        if alias is not None:
            normalized["selected_agent"] = alias

    seci_mode = normalized.get("seci_mode")
    if isinstance(seci_mode, str):
        alias = SECI_ALIASES.get(seci_mode.strip().lower())
        if alias is not None:
            normalized["seci_mode"] = alias

    reuse_situation = normalized.get("reuse_situation")
    if isinstance(reuse_situation, str):
        alias = REUSE_ALIASES.get(reuse_situation.strip().lower())
        if alias is not None:
            normalized["reuse_situation"] = alias

    routing_confidence = normalized.get("routing_confidence")
    if isinstance(routing_confidence, (int, float)):
        score = float(routing_confidence)
        if score >= 0.85:
            normalized["routing_confidence"] = "high"
        elif score >= 0.5:
            normalized["routing_confidence"] = "medium"
        else:
            normalized["routing_confidence"] = "low"
    elif isinstance(routing_confidence, str):
        lowered = routing_confidence.strip().lower()
        if lowered in {"high", "medium", "low"}:
            normalized["routing_confidence"] = lowered

    required_context = normalized.get("required_context")
    if isinstance(required_context, str):
        value = required_context.strip()
        normalized["required_context"] = [value] if value else []
    elif not isinstance(required_context, list):
        normalized["required_context"] = []

    verification_need = normalized.get("verification_need")
    if isinstance(verification_need, bool):
        normalized["verification_need"] = "user confirmation required" if verification_need else "none"
    elif verification_need is None:
        normalized["verification_need"] = "none"
    else:
        normalized["verification_need"] = str(verification_need).strip() or "none"

    next_state = normalized.get("next_state")
    if next_state is None:
        normalized["next_state"] = "agent_execution"
    else:
        normalized["next_state"] = str(next_state).strip() or "agent_execution"

    reason = normalized.get("reason")
    normalized["reason"] = str(reason).strip() if reason is not None else ""

    normalized.pop("model_selection", None)

    return RouterPayload.model_validate(normalized)


def get_relevant_history(
    user_id: str,
    query_embedding: bytes | None = None,
    since_days: int = 30,
    current_session_id: str | None = None,
) -> dict[str, Any]:
    """Query session history for relevant context"""
    if not user_id:
        return {"recurring_themes": [], "uncaptured_themes": [], "related_sessions": []}

    since_days = max(int(since_days), 1)
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("SELECT datetime('now', ?)", (f"-{since_days} days",))
    cutoff_date = cursor.fetchone()[0]

    params: list[Any] = [user_id, cutoff_date]
    session_filter = ""
    if current_session_id:
        session_filter = "AND session_id != ?"
        params.append(current_session_id)

    cursor.execute(
        f"""
        SELECT session_id, session_title, router_classification, user_query,
               generated_artefacts, citations_used, timestamp
        FROM session_history
        WHERE user_id = ? AND timestamp > ?
        {session_filter}
        ORDER BY timestamp DESC
        LIMIT 10
        """,
        params,
    )

    rows = cursor.fetchall()

    # Process the results for recurring theme detection
    recurring_themes = []
    uncaptured_themes = []
    related_sessions: list[dict[str, Any]] = []

    for row in rows:
        classification = json.loads(row["router_classification"]) if row["router_classification"] else {}
        if classification:
            # Extract potential recurring themes from previous classifications
            for key in ("seci_mode", "knowledge_mode", "reuse_situation", "distance", "role"):
                value = classification.get(key)
                if value:
                    recurring_themes.append(str(value))

        artefacts = json.loads(row["generated_artefacts"]) if row["generated_artefacts"] else []
        citations = json.loads(row["citations_used"]) if row["citations_used"] else []
        related_sessions.append(
            {
                "session_id": row["session_id"],
                "title": row["session_title"] or "Previous session",
                "query": row["user_query"] or "",
                "timestamp": row["timestamp"],
                "generated_artefacts": artefacts[:5] if isinstance(artefacts, list) else [],
                "citations_used": citations[:5] if isinstance(citations, list) else [],
            }
        )

    return {
        "recurring_themes": list(set(recurring_themes)),
        "uncaptured_themes": list(set(uncaptured_themes)),  # Placeholder for future logic
        "related_sessions": related_sessions,
    }


def get_session_similarity_score(user_id: str, query_text: str, since_days: int = 30) -> float:
    """Calculate similarity score between current query and session history"""
    # This is a simplified implementation - in a real system we'd compute actual embeddings
    # and compare them for similarity
    return 0.0


@traceable(name="router_agent_route", run_type="chain")
def route_with_agent(
    backend,
    *,
    user_input: str,
    chat_history: list[dict[str, str]] | None = None,
    session_ctx: dict | None = None,
) -> RouteDecision:
    session_ctx = session_ctx or {}
    user_id = session_ctx.get("user_id")
    session_insights = {"recurring_themes": [], "uncaptured_themes": [], "related_sessions": []}
    if user_id:
        session_insights = get_relevant_history(
            user_id,
            since_days=30,
            current_session_id=session_ctx.get("session_id"),
        )
        session_ctx["session_insights"] = session_insights

    prompt = build_router_prompt(user_input, chat_history, session_insights=session_insights)

    raw = backend.generate(
        prompt,
        system_prompt=ROUTER_SYSTEM_PROMPT,
        temperature=0.0,
        response_format={"type": "json_object"},
    )
    parsed = _load_json_object(raw)
    payload = _normalize_router_payload(parsed)

    return RouteDecision(
        role=payload.selected_agent,
        knowledge_mode=SECI_TO_KNOWLEDGE_MODE[payload.seci_mode],
        distance=REUSE_TO_DISTANCE[payload.reuse_situation],
        routing_confidence=payload.routing_confidence,
        reason=payload.reason,
        required_context=payload.required_context,
        verification_need=payload.verification_need,
        next_state=payload.next_state,
        used_fallback=False,
        model_selection=model_selection_for_role(payload.selected_agent),
        detected_themes=session_insights.get("recurring_themes", []),
        knowledge_gaps=session_insights.get("uncaptured_themes", []),
        related_sessions=session_insights.get("related_sessions", []),
    )
