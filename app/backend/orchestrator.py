from __future__ import annotations

import json
from typing import Any

from app.domain.types import TurnRecord
from app.backend import sqlite_store
from app.backend.intent_distance import classify_intent
from app.backend.router_agent import route_with_agent, get_relevant_history
from app.backend.fsm import decide_state
from app.backend.retrieval import run_retrieval
from app.infrastructure.tracing import traceable
from app.domain.schema import AssistantPayload
from app.backend.sqlite_store import create_session, init_db, log_turn, save_artefacts, get_conn
from app.backend.user_scope import user_workspace_id
from app.backend.llm_client import LLMClient
from app.prompts.prompts import get_role_prompt
from app.rag.llm import OpenAIChatBackend
from app.infrastructure.config import (
    ROUTER_MODEL_NAME,
    SCRIBE_MODEL_NAME,
    SEMANTIC_LINKING_MODEL_NAME,
    MENTOR_MODEL_NAME,
    CONTEXT_RECONSTRUCTOR_MODEL_NAME,
    LLM_MODEL_NAME
)


def _chat_backend(model_name: str | None = None):
    try:
        return OpenAIChatBackend(model_name=model_name)
    except TypeError:
        return OpenAIChatBackend()


def build_session_title(user_input: str, max_chars: int = 48) -> str:
    title = " ".join(user_input.strip().split())
    if not title:
        return "New chat"
    if len(title) <= max_chars:
        return title
    if max_chars <= 3:
        return title[:max_chars]
    return title[: max_chars - 3].rstrip() + "..."


def store_session_history(
    session_id: str,
    user_id: str | None,
    user_input: str,
    router_classification: Any,
    generated_artefacts: list,
    citations_used: list,
    user_feedback: dict | None = None
) -> None:
    """Store session information for future routing decisions"""
    sqlite_store.init_db()
    conn = get_conn()
    with conn:
        # Convert router_classification to dict if it's an object
        if hasattr(router_classification, '__dict__'):
            classification_dict = router_classification.__dict__
        elif isinstance(router_classification, dict):
            classification_dict = router_classification
        else:
            # Handle case where it's a simple namespace or other object
            classification_dict = {
                'role': getattr(router_classification, 'role', ''),
                'knowledge_mode': getattr(router_classification, 'knowledge_mode', ''),
                'distance': getattr(router_classification, 'distance', ''),
                'routing_confidence': getattr(router_classification, 'routing_confidence', ''),
                'reason': getattr(router_classification, 'reason', ''),
                'required_context': getattr(router_classification, 'required_context', []),
                'verification_need': getattr(router_classification, 'verification_need', ''),
                'next_state': getattr(router_classification, 'next_state', ''),
                'used_fallback': getattr(router_classification, 'used_fallback', False),
            }
        
        conn.execute("""
            INSERT INTO session_history (
                session_id, user_id, session_title, timestamp, router_classification,
                user_query, generated_artefacts, citations_used, user_feedback
            ) VALUES (?, ?, ?, datetime('now'), ?, ?, ?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
                user_id = excluded.user_id,
                session_title = COALESCE(session_history.session_title, excluded.session_title),
                timestamp = excluded.timestamp,
                router_classification = excluded.router_classification,
                user_query = excluded.user_query,
                generated_artefacts = excluded.generated_artefacts,
                citations_used = excluded.citations_used,
                user_feedback = excluded.user_feedback
        """, (
            session_id,
            user_id,
            build_session_title(user_input),
            json.dumps(classification_dict),
            user_input,
            json.dumps(generated_artefacts),
            json.dumps(citations_used),
            json.dumps(user_feedback) if user_feedback else None
        ))


def build_session_ctx(session_id: str, user_id: str | None = None) -> dict[str, Any]:
    """
    Placeholder for future session restoration.
    For now, returns an authenticated user context when available.
    """
    if user_id:
        return build_user_profile(user_id)
    return {}


def build_user_profile(user_id: str | None) -> dict[str, Any]:
    """
    Placeholder for future user profile loading.
    """
    return {"language": "de", "user_id": user_id}


def build_prompt(
    user_input: str,
    role: str,
    role_instructions: str,
    state: str | None,
    retrieved_chunks: list[dict[str, Any]],
    intent: str,
    distance: str,
    knowledge_mode: str,
    confidence: float,
    chat_history: list[dict[str, str]] | None = None,
) -> str:
    schema_example = {
        "role": role,
        "state": state,
        "assistant_message": "Kurze, direkte Antwort auf die Nutzeranfrage.",
        "questions": [],
        "artefacts": [],
        "actions": [{"type": "none", "payload": {}}],
        "citations": [],
        "telemetry": {
            "intent": intent,
            "distance": distance,
            "confidence": round(confidence, 3),
            "retrieval_count": min(len(retrieved_chunks), 5),
            "repair_used": False,
            "fallback_used": False,
        },
    }

    context_lines: list[str] = []
    for i, chunk in enumerate(retrieved_chunks[:5], start=1):
        locator = f"p. {chunk['page']}" if chunk.get("page") is not None else "unknown"
        context_lines.append(
            "\n".join(
                [
                    (
                        f"[{i}] chunk_id={chunk['chunk_id']} "
                        f"source={chunk['source']} locator={locator}"
                    ),
                    chunk["text"],
                ]
            )
        )

    context_block = "\n\n".join(context_lines) if context_lines else "(kein Retrieval-Kontext)"

    history_lines: list[str] = []
    for turn in (chat_history or [])[-5:]:
        user_turn = turn.get("user", "").strip()
        assistant_turn = turn.get("assistant", "").strip()
        if user_turn:
            history_lines.append(f"Nutzer: {user_turn}")
        if assistant_turn:
            history_lines.append(f"Assistant: {assistant_turn}")

    history_block = "\n".join(history_lines) if history_lines else "(keine bisherige Unterhaltung)"

    return f"""
Du bist {role}.
Antworte ausschließlich als JSON entsprechend dem definierten Schema.
Keine Markdown-Umrandung.
Kein Zusatztext außerhalb des JSON.

Gib genau diese Felder zurück:
- role
- state
- assistant_message
- questions
- artefacts
- actions
- citations
- telemetry

Wichtige Regeln:
- role muss "{role}" sein.
- state muss {"null" if state is None else f'"{state}"'} sein.
- assistant_message muss immer ein nicht-leerer String sein.
- questions, artefacts, actions und citations müssen Arrays sein.
- actions muss mindestens ein Objekt mit `type` und `payload` enthalten.
- citations dürfen nur chunk_id-Werte aus dem Retrieved Context referenzieren.
- Wenn kein Retrieval-Kontext vorhanden ist, beantworte die Anfrage trotzdem mit allgemeinem Wissen und lasse citations leer.
- Wenn die Anfrage knapp ist, interpretiere sie sinnvoll statt reflexhaft nachzufragen.
- telemetry muss diese Werte enthalten:
  - intent: "{intent}"
  - distance: "{distance}"
  - confidence: {confidence:.3f}
  - retrieval_count: {min(len(retrieved_chunks), 5)}
  - repair_used: false
  - fallback_used: false

Kontext:
- intent: {intent}
- distance: {distance}
- knowledge_mode: {knowledge_mode}
- confidence: {confidence:.3f}
- state: {state}

Rollenanweisung:
{role_instructions}

Nutzeranfrage:
{user_input}

Bisherige Unterhaltung:
{history_block}

Retrieved Context:
{context_block}

Beispiel für die Zielstruktur:
{json.dumps(schema_example, ensure_ascii=False)}
""".strip()


def merge_citations(
    model_citations: list[dict[str, Any]],
    retrieved_chunks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    for citation in model_citations:
        key = (citation["source"], citation["chunk_id"])
        if key in seen:
            continue
        seen.add(key)
        merged.append(citation)

    for chunk in retrieved_chunks[:5]:
        citation = {
            "source": chunk["source"],
            "chunk_id": chunk["chunk_id"],
            "title": chunk.get("title"),
            "locator": f"p. {chunk['page']}" if chunk.get("page") is not None else None,
        }
        key = (citation["source"], citation["chunk_id"])
        if key in seen:
            continue
        seen.add(key)
        merged.append(citation)

    return merged


@traceable(name="handle_turn", run_type="chain")
def handle_turn(
    session_id: str,
    user_input: str,
    user_id: str | None = None,
    *,
    collection_name: str = "default",
    chat_history: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """
    Main orchestration entrypoint.

    Flow:
    1. ensure session exists
    2. classify intent + estimate distance
    3. run retrieval and compute confidence
    4. route role
    5. decide tutor FSM state
    6. build prompt
    7. call LLM with strict JSON handling
    8. validate final payload
    9. persist turn + artefacts
    10. return schema-valid payload
    """
    init_db()
    create_session(session_id)

    if user_id and collection_name == "default":
        collection_name = user_workspace_id(user_id)

    session_ctx = build_session_ctx(session_id, user_id)

    intent = classify_intent(user_input)

    # Route the request first to determine the agent role
    backend = _chat_backend(ROUTER_MODEL_NAME)
    route = route_with_agent(
        backend,
        user_input=user_input,
        chat_history=chat_history,
        session_ctx=session_ctx,
    )
    distance = route.distance
    knowledge_mode = route.knowledge_mode
    role = route.role
    
    # Store session history after routing (before executing the agent)
    # This ensures we have context for the next request
    store_session_history(
        session_id=session_id,
        user_id=user_id,
        user_input=user_input,
        router_classification=route,
        generated_artefacts=[],
        citations_used=[]
    )
    
    # Use model selection information from router if available
    model_name = LLM_MODEL_NAME
    model_selection = getattr(route, "model_selection", None)
    if model_selection and "model_name" in model_selection:
        model_name = model_selection["model_name"]
    else:
        # Fallback to legacy model selection logic
        # Determine the appropriate model for this agent
        if role == "ScribeAgent":
            model_name = SCRIBE_MODEL_NAME
        elif role == "SemanticLinkingAgent":
            model_name = SEMANTIC_LINKING_MODEL_NAME
        elif role == "MentorAgent":
            model_name = MENTOR_MODEL_NAME
        elif role == "ContextReconstructorAgent":
            model_name = CONTEXT_RECONSTRUCTOR_MODEL_NAME
        else:
            # Default to the main LLM model for other agents
            model_name = LLM_MODEL_NAME
    
    # Now create the backend with the appropriate model
    backend = _chat_backend(model_name)

    retrieval = run_retrieval(
        query=user_input,
        collection_name=collection_name,
    )
    confidence = retrieval["confidence"]

    role_instructions = get_role_prompt(role)

    state = decide_state(
        role=role,
        retrieval_confidence=confidence,
        session_ctx=session_ctx,
        force_tutor_mode=False,
    )

    # Pass session history insights to FSM if available
    if hasattr(route, 'detected_themes'):
        session_ctx['detected_themes'] = route.detected_themes
    if hasattr(route, 'knowledge_gaps'):
        session_ctx['knowledge_gaps'] = route.knowledge_gaps

    prompt = build_prompt(
        user_input=user_input,
        role=role,
        role_instructions=role_instructions,
        state=state,
        retrieved_chunks=retrieval["chunks"],
        intent=intent,
        distance=distance,
        knowledge_mode=knowledge_mode,
        confidence=confidence,
        chat_history=chat_history,
    )

    client = LLMClient(backend)

    payload = client.generate_json(
        prompt,
        fallback_role=role,
        fallback_state=state,
        fallback_intent=intent,
        fallback_distance=distance,
        fallback_confidence=confidence,
        fallback_retrieval_count=len(retrieval["chunks"]),
    )

    # Ensure telemetry reflects actual orchestration values
    payload["telemetry"]["intent"] = intent
    payload["telemetry"]["distance"] = distance
    payload["telemetry"]["confidence"] = confidence
    payload["telemetry"]["retrieval_count"] = len(retrieval["chunks"])
    payload["router_debug"] = {
        "role": route.role,
        "knowledge_mode": route.knowledge_mode,
        "distance": route.distance,
        "model_name": model_name,
        "model_reason": (model_selection or {}).get("reason", "Chosen by the default configured language model."),
        "routing_confidence": route.routing_confidence,
        "reason": route.reason,
        "required_context": route.required_context,
        "verification_need": route.verification_need,
        "next_state": route.next_state,
        "used_fallback": route.used_fallback,
    }
    payload["citations"] = merge_citations(payload["citations"], retrieval["chunks"])

    # Final hard validation
    validated = AssistantPayload.model_validate(payload)
    payload = validated.model_dump()

    turn = TurnRecord(
        session_id=session_id,
        user_id=user_id,
        user_input=user_input,
        intent=intent,
        distance=distance,
        role=payload["role"],
        state=payload["state"],
        confidence=confidence,
        llm_json=json.dumps(payload, ensure_ascii=False),
        system_state=json.dumps(
            {
                "role": payload["role"],
                "state": payload["state"],
                "intent": intent,
                "distance": distance,
                "confidence": confidence,
            },
            ensure_ascii=False,
        ),
    )
    log_turn(turn)

    # Store session history for future routing
    generated_artefacts = [a["title"] for a in payload["artefacts"]] if payload["artefacts"] else []
    citations_used = [c["chunk_id"] for c in payload["citations"]] if payload["citations"] else []
    store_session_history(
        session_id=session_id,
        user_id=user_id,
        user_input=user_input,
        router_classification=route,
        generated_artefacts=generated_artefacts,
        citations_used=citations_used
    )

    if payload["artefacts"]:
        refs = [
            {"ref_type": "chunk", "ref_id": chunk["chunk_id"]}
            for chunk in retrieval["chunks"][:5]
        ]
        save_artefacts(
            artefacts=payload["artefacts"],
            project=collection_name,
            refs=refs,
        )

    return payload
