from __future__ import annotations

import json
from dataclasses import dataclass, field
from json import JSONDecodeError
from typing import Any

from app.backend.intent_distance import classify_intent, estimate_distance, infer_knowledge_mode
from app.backend.role_router import role_router
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


@dataclass(frozen=True)
class RouteDecision:
    role: RoleName
    knowledge_mode: KnowledgeMode
    distance: Distance
    routing_confidence: str
    reason: str
    required_context: list[str]
    verification_need: str
    next_state: str
    used_fallback: bool = False
    model_selection: dict[str, Any] = field(default_factory=dict)


def build_router_prompt(
    user_input: str,
    chat_history: list[dict[str, str]] | None = None,
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

    return json.dumps(
        {
            "available_agents": AGENT_REGISTRY,
            "user_request": user_input,
            "chat_history": history_block,
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


def _heuristic_route(user_input: str, session_ctx: dict) -> RouteDecision:
    intent = classify_intent(user_input)
    distance = estimate_distance(user_input, intent)
    knowledge_mode = infer_knowledge_mode(user_input, intent, distance)
    role = role_router(intent=intent, distance=distance, knowledge_mode=knowledge_mode, session_ctx=session_ctx)
    return RouteDecision(
        role=role,
        knowledge_mode=knowledge_mode,
        distance=distance,
        routing_confidence="low",
        reason="Fallback to heuristic router because the router agent was unavailable or invalid.",
        required_context=[],
        verification_need="none",
        next_state="agent_execution",
        used_fallback=True,
        model_selection=model_selection_for_role(role),
    )


def _load_json_object(raw: str) -> dict:
    text = raw.strip()
    try:
        parsed = json.loads(text)
    except JSONDecodeError as exc:
        raise JSONDecodeError(exc.msg, exc.doc, exc.pos) from exc
    if not isinstance(parsed, dict):
        raise JSONDecodeError("Router output was not a JSON object.", text, 0)
    return parsed


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


@traceable(name="router_agent_route", run_type="chain")
def route_with_agent(
    backend,
    *,
    user_input: str,
    chat_history: list[dict[str, str]] | None = None,
    session_ctx: dict | None = None,
) -> RouteDecision:
    session_ctx = session_ctx or {}
    prompt = build_router_prompt(user_input, chat_history)

    try:
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
        )
    except Exception:
        return _heuristic_route(user_input, session_ctx)
