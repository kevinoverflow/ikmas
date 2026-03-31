from __future__ import annotations

import json
from typing import Any

from app.domain.types import TurnRecord
from app.backend.intent_distance import classify_intent, estimate_distance
from app.backend.role_router import role_router
from app.backend.fsm import decide_state
from app.backend.retrieval import run_retrieval
from app.domain.schema import AssistantPayload
from app.backend.sqlite_store import create_session, log_turn, save_artefacts
from app.backend.llm_client import LLMClient
from app.rag.llm import OpenAIChatBackend


def build_session_ctx(session_id: str) -> dict[str, Any]:
    """
    Placeholder for future session restoration.
    For now, returns an empty session context.
    """
    return {}


def build_user_profile(user_id: str | None) -> dict[str, Any]:
    """
    Placeholder for future user profile loading.
    """
    return {"language": "de", "user_id": user_id}


def build_prompt(
    user_input: str,
    role: str,
    state: str | None,
    retrieved_chunks: list[dict[str, Any]],
    intent: str,
    distance: str,
    confidence: float,
) -> str:
    context_block = "\n\n".join(
        f"[{i + 1}] {chunk['text']}"
        for i, chunk in enumerate(retrieved_chunks[:5])
    )

    return f"""
Du bist {role}.
Antworte ausschließlich als JSON entsprechend dem definierten Schema.
Keine Markdown-Umrandung.
Kein Zusatztext außerhalb des JSON.

Kontext:
- intent: {intent}
- distance: {distance}
- confidence: {confidence:.3f}
- state: {state}

Nutzeranfrage:
{user_input}

Retrieved Context:
{context_block}
""".strip()


def handle_turn(session_id: str, user_input: str, user_id: str | None = None) -> dict[str, Any]:
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
    create_session(session_id)

    session_ctx = build_session_ctx(session_id)
    user_profile = build_user_profile(user_id)

    intent = classify_intent(user_input)
    distance = estimate_distance(user_input, intent)

    retrieval = run_retrieval(user_input)
    confidence = retrieval["confidence"]

    role = route_role(
        intent=intent,
        distance=distance,
        retrieval_confidence=confidence,
        user_profile=user_profile,
        session_ctx=session_ctx,
    )

    state = decide_state(
        role=role,
        retrieval_confidence=confidence,
        session_ctx=session_ctx,
        force_tutor_mode=(intent == "learn_mode"),
    )

    prompt = build_prompt(
        user_input=user_input,
        role=role,
        state=state,
        retrieved_chunks=retrieval["chunks"],
        intent=intent,
        distance=distance,
        confidence=confidence,
    )

    backend = OpenAIChatBackend()
    client = LLMClient(backend)

    payload = client.generate_json(
        prompt,
        fallback_role="TutoringAgent" if role == "TutoringAgent" else "MentorAgent",
        fallback_state="ASSESS" if role == "TutoringAgent" else None,
        fallback_intent=intent,
        fallback_distance=distance,
        fallback_confidence=confidence,
        fallback_retrieval_count=len(retrieval["chunks"]),
    )

    # Final hard validation
    validated = AssistantPayload.model_validate(payload)
    payload = validated.model_dump()

    # Ensure telemetry reflects actual orchestration values
    payload["telemetry"]["intent"] = intent
    payload["telemetry"]["distance"] = distance
    payload["telemetry"]["confidence"] = confidence
    payload["telemetry"]["retrieval_count"] = len(retrieval["chunks"])

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

    if payload["artefacts"]:
        refs = [
            {"ref_type": "chunk", "ref_id": chunk["chunk_id"]}
            for chunk in retrieval["chunks"][:5]
        ]
        save_artefacts(
            artefacts=payload["artefacts"],
            project="default",
            refs=refs,
        )

    return payload