from __future__ import annotations

from typing import Any

from app.backend.artefacts import persist_artefacts_with_links
from app.backend.conversation_logger import log_conversation_event
from app.backend.fsm import decide_state
from app.backend.intent_distance import classify_intent, estimate_distance
from app.backend.llm_client import call_llm_json, repair_llm_json
from app.backend.retrieval import retrieve_bundle
from app.backend.role_gate import (
    build_post_response_role_questions,
    infer_intent_distance_from_gate_answers,
    parse_role_gate_answers,
)
from app.backend.role_router import route_role
from app.backend.schema import fallback_payload, validate_or_raise
from app.backend.sqlite_store import (
    TurnRecord,
    create_session,
    get_recent_turns,
    get_session_context,
    get_user_profile,
    init_db,
    log_turn,
)


def _build_context_text(docs: list[Any], max_chars: int = 8000) -> tuple[str, list[dict]]:
    chunks: list[str] = []
    citations: list[dict] = []

    for i, d in enumerate(docs):
        src = d.metadata.get("source", "unknown")
        start = d.metadata.get("start_index", 0)
        page = d.metadata.get("page", "NA")
        source_id = f"{src}#chunk{start}#p{page}"
        score = float(d.metadata.get("rerank_score", 0.0) or 0.0)
        citations.append({"source_id": source_id, "score": max(0.0, min(1.0, score))})
        chunks.append(f"[{i+1}] ({source_id})\n{d.page_content}")

    context = "\n\n".join(chunks)
    if len(context) > max_chars:
        context = context[:max_chars]
    return context, citations


def _needs_followup(confidence: float) -> bool:
    return confidence < 0.75


def _set_common_response_fields(payload: dict[str, Any], confidence: float, mode: str, phase: str) -> dict[str, Any]:
    payload["mode"] = mode
    payload["interaction_phase"] = phase
    payload.setdefault("telemetry", {})
    payload["telemetry"]["confidence"] = max(0.0, min(1.0, float(confidence)))
    payload["telemetry"]["needs_followup"] = _needs_followup(confidence)
    return payload


def handle_turn(
    session_id: str,
    user_input: str,
    user_id: str | None = None,
    role_override: str | None = None,
) -> dict:
    init_db()
    create_session(session_id)

    profile = get_user_profile(user_id)
    session_ctx = get_session_context(session_id)

    gate_answers = parse_role_gate_answers(user_input)
    intent = classify_intent(user_input)
    distance = estimate_distance(user_input, profile)

    if gate_answers:
        intent, distance = infer_intent_distance_from_gate_answers(gate_answers)

    retrieval = retrieve_bundle(collection_name="default", query=user_input, k_retrieve=30, k_final=5)

    force_tutor_mode = intent == "learn_mode"
    if force_tutor_mode:
        session_ctx["force_tutor_mode"] = True

    role = role_override or route_role(
        intent=intent,
        distance=distance,
        retrieval_confidence=retrieval.confidence,
        user_profile=profile,
        session_ctx=session_ctx,
        role_gate_answers=gate_answers,
    )

    state = decide_state(
        role=role,
        retrieval_confidence=retrieval.confidence,
        session_ctx=session_ctx,
        force_tutor_mode=force_tutor_mode,
    )

    context_text, citations = _build_context_text(retrieval.docs)
    chat_history = get_recent_turns(session_id, limit=5)

    raw_output = ""
    try:
        payload, raw_output = call_llm_json(
            role=role,
            state=state,
            user_input=user_input,
            intent=intent,
            distance=distance,
            confidence=retrieval.confidence,
            retrieved_context=context_text,
            citations=citations,
            chat_history=chat_history,
        )
        payload = _set_common_response_fields(payload, retrieval.confidence, "assistant_response", "ASSISTANT")
        payload = validate_or_raise(payload)
    except Exception as first_error:
        try:
            payload, _ = repair_llm_json(
                invalid_output=raw_output or str(first_error),
                error_message=str(first_error),
            )
            payload = _set_common_response_fields(payload, retrieval.confidence, "assistant_response", "ASSISTANT")
            payload = validate_or_raise(payload)
        except Exception:
            payload = fallback_payload(role=role, state=state, confidence=retrieval.confidence)
            payload = _set_common_response_fields(payload, retrieval.confidence, "assistant_response", "ASSISTANT")
            payload = validate_or_raise(payload)

    role_questions = build_post_response_role_questions(
        user_input=user_input,
        assistant_message=payload.get("assistant_message", ""),
        intent=intent,
        distance=distance,
        role_gate_answers=gate_answers,
        role_override=role_override,
        previous_questions=payload.get("questions", []),
    )
    payload["questions"] = role_questions
    payload["telemetry"]["needs_followup"] = bool(role_questions) or _needs_followup(retrieval.confidence)
    payload = validate_or_raise(payload)

    system_state = {
        "gate_status": "ROLE_GATE_RESOLVED" if gate_answers else "ROLE_GATE_OPEN",
        "pending_role_gate": bool(role_questions and not gate_answers),
        "role_gate_questions": role_questions,
        "role_gate_answers": gate_answers or {},
        "intent": intent,
        "distance": distance,
        "force_tutor_mode": bool(session_ctx.get("force_tutor_mode", False)),
        "retrieval": {
            "top1": retrieval.top1,
            "avg_top3": retrieval.avg_top3,
            "coverage": retrieval.coverage,
            "confidence": retrieval.confidence,
        },
    }

    log_turn(
        TurnRecord(
            session_id=session_id,
            user_message=user_input,
            chosen_role=payload.get("role", role),
            retrieval_confidence=retrieval.confidence,
            system_state=system_state,
            llm_json=payload,
        )
    )

    persist_artefacts_with_links(
        artefacts=payload.get("artefacts", []),
        citations=payload.get("citations", citations),
        project="default",
    )

    # Append JSONL analytics event for offline conversation evaluation.
    log_conversation_event(
        session_id=session_id,
        user_id=user_id,
        user_message=user_input,
        payload=payload,
        system_state=system_state,
        role_override=role_override,
    )

    return payload
