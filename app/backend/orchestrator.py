from __future__ import annotations

"""
Main orchestrator for coordinating the IKMAS runtime pipeline.
"""

import json
from typing import Any

from app.backend.artifact_reuse_agent import artifact_reuse_agent
from app.backend.artifact_generators.concept_generator import estimate_concept_count
from app.backend.artifact_generators.definition_generator import estimate_definition_count
from app.backend.artifact_generators.quiz_generator import estimate_quiz_item_count
from app.backend.fsm import decide_state
from app.backend.llm_client import LLMClient
from app.backend.retrieval import run_retrieval
from app.backend.router_agent import (
    model_selection_for_role,
    normalize_artifact_generation_plan,
    route_with_agent,
)
from app.backend.sqlite_store import (
    create_session,
    get_conn,
    init_db,
    log_turn,
    save_artefacts,
)
from app.backend.artifact_models import (
    ArtifactGenerationRequest,
    ArtifactType,
)
from app.backend.subagent_coordinator import (
    subagent_coordinator,
)
from app.domain.schema import AssistantPayload
from app.domain.types import TurnRecord
from app.prompts.prompts import get_role_prompt
from app.rag.llm import OpenAIChatBackend


ARTIFACT_TITLES = {
    "definition": "Definition",
    "concept": "Concept Explanation",
    "quiz_item": "Quiz Item",
}


def create_chat_backend(model_name: str | None = None):
    try:
        return OpenAIChatBackend(model_name=model_name)
    except TypeError:
        return OpenAIChatBackend()


def build_session_title(user_input: str, max_chars: int = 80) -> str:
    normalized = " ".join(user_input.split()).strip()
    if len(normalized) <= max_chars:
        return normalized or "Untitled session"
    return normalized[: max_chars - 3].rstrip() + "..."


def _collection_for_user(collection_name: str | None, user_id: str | None) -> str:
    if collection_name:
        return collection_name
    if user_id:
        return f"u_{user_id}__default"
    return "default"


def _route_as_dict(route: Any) -> dict[str, Any]:
    if hasattr(route, "model_dump"):
        return route.model_dump()
    if isinstance(route, dict):
        return route
    return {
        key: value
        for key, value in vars(route).items()
        if not key.startswith("_")
    }


def _format_history(chat_history: list[dict[str, str]] | None) -> str:
    lines: list[str] = []
    for turn in (chat_history or [])[-6:]:
        user_turn = (turn.get("user") or "").strip()
        assistant_turn = (turn.get("assistant") or turn.get("bot") or "").strip()
        if user_turn:
            lines.append(f"Nutzer: {user_turn}")
        if assistant_turn:
            lines.append(f"Assistent: {assistant_turn}")
    return "\n".join(lines) if lines else "(keine bisherige Unterhaltung)"


def _format_chunks(retrieved_chunks: list[dict[str, Any]]) -> str:
    if not retrieved_chunks:
        return (
            "Kein Retrieval-Kontext gefunden. Wenn kein Retrieval-Kontext vorhanden ist, "
            "beantworte allgemeine Wissensfragen mit deinem allgemeinen Wissen und kennzeichne, "
            "dass keine projektspezifischen Quellen verwendet wurden."
        )

    blocks: list[str] = []
    for idx, chunk in enumerate(retrieved_chunks, 1):
        title = chunk.get("title") or chunk.get("source") or "unknown"
        page = chunk.get("page")
        locator = f"p. {page}" if page is not None else "no page"
        text = (chunk.get("text") or "").strip()
        blocks.append(
            f"[{idx}] {title} ({locator}) chunk={chunk.get('chunk_id', 'unknown')}\n{text}"
        )
    return "\n\n".join(blocks)


def _format_session_context(session_ctx: dict[str, Any] | None) -> str:
    session_ctx = session_ctx or {}
    lines = ["Session Context:"]

    detected_themes = session_ctx.get("detected_themes") or []
    knowledge_gaps = session_ctx.get("knowledge_gaps") or []
    related_sessions = session_ctx.get("related_sessions") or []

    lines.append("Detected themes: " + (", ".join(detected_themes) if detected_themes else "none"))
    lines.append("Knowledge gaps: " + (", ".join(knowledge_gaps) if knowledge_gaps else "none"))

    if related_sessions:
        lines.append("Related sessions:")
        for session in related_sessions[:5]:
            artefacts = session.get("generated_artefacts") or []
            lines.append(
                "- "
                f"{session.get('title') or 'Previous session'}: "
                f"{session.get('query') or ''} "
                f"(artefacts: {', '.join(artefacts) if artefacts else 'none'})"
            )
    else:
        lines.append("Related sessions: none")

    return "\n".join(lines)


def build_prompt(
    *,
    user_input: str,
    role: str,
    role_instructions: str,
    state: str | None,
    retrieved_chunks: list[dict[str, Any]],
    intent: str,
    distance: str,
    knowledge_mode: str,
    confidence: float,
    chat_history: list[dict[str, str]] | None,
    session_ctx: dict[str, Any] | None,
) -> str:
    response_schema = {
        "role": role,
        "state": state,
        "assistant_message": "string",
        "questions": [],
        "artefacts": [],
        "actions": [{"type": "none", "payload": {}}],
        "citations": [],
        "telemetry": {
            "intent": intent,
            "distance": distance,
            "confidence": confidence,
            "retrieval_count": len(retrieved_chunks),
            "repair_used": False,
            "fallback_used": False,
        },
    }

    return "\n\n".join(
        [
            "Rollenanweisung:",
            role_instructions,
            "Routing:",
            f"role: {role}",
            f"state: {state}",
            f"intent: {intent}",
            f"distance: {distance}",
            f"knowledge_mode: {knowledge_mode}",
            f"confidence: {confidence}",
            _format_session_context(session_ctx),
            "Chat History:",
            _format_history(chat_history),
            "Retrieval Context:",
            _format_chunks(retrieved_chunks),
            "User Request:",
            user_input,
            "Return valid JSON matching this shape:",
            json.dumps(response_schema, ensure_ascii=False, indent=2),
        ]
    )


def merge_citations(
    model_citations: list[dict[str, Any]],
    retrieved_chunks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()

    for citation in model_citations:
        chunk_id = str(citation.get("chunk_id") or "")
        source = citation.get("source")
        if not chunk_id or not source or chunk_id in seen:
            continue
        merged.append(citation)
        seen.add(chunk_id)

    for chunk in retrieved_chunks:
        chunk_id = str(chunk.get("chunk_id") or "")
        source = str(chunk.get("source") or "")
        if not chunk_id or not source or chunk_id in seen:
            continue
        page = chunk.get("page")
        merged.append(
            {
                "source": source,
                "chunk_id": chunk_id,
                "title": chunk.get("title"),
                "locator": f"p. {page}" if page is not None else None,
            }
        )
        seen.add(chunk_id)

    return merged


def _artifact_context(user_input: str, retrieved_chunks: list[dict[str, Any]]) -> str:
    chunk_texts = [
        str(chunk.get("text") or "").strip()
        for chunk in retrieved_chunks[:5]
        if str(chunk.get("text") or "").strip()
    ]
    if chunk_texts:
        return "\n\n".join(chunk_texts)
    return user_input


def _subagent_request(
    *,
    artifact_type: str,
    user_input: str,
    retrieved_chunks: list[dict[str, Any]],
    session_id: str,
    related_artifacts: list[dict[str, Any]],
    target_audience: str,
) -> ArtifactGenerationRequest:
    return ArtifactGenerationRequest(
        artifact_type=ArtifactType(artifact_type),
        context=_artifact_context(user_input, retrieved_chunks),
        user_input=user_input,
        session_id=session_id,
        related_artifacts=related_artifacts,
        target_audience=target_audience,
    )


def _artifact_from_subagent_result(result) -> dict[str, Any]:
    artifact_type = result.artifact_type.value
    return {
        "type": artifact_type,
        "title": ARTIFACT_TITLES.get(artifact_type, artifact_type.replace("_", " ").title()),
        "content": result.content,
        "concept_ids": [],
    }


def _artifact_from_stored(stored_artifact: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": stored_artifact["type"],
        "title": stored_artifact["title"],
        "content": stored_artifact["content"],
        "concept_ids": stored_artifact.get("concept_ids", []),
        "_artifact_id": stored_artifact.get("id"),
        "_reused": True,
    }


def _strip_internal_artifact_fields(artifact: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in artifact.items()
        if not str(key).startswith("_")
    }


def _artifact_fingerprint(artifact: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(artifact.get("type") or ""),
        str(artifact.get("title") or ""),
        str(artifact.get("content") or ""),
    )


def _format_quiz_item_content(item: dict[str, Any]) -> str:
    lines: list[str] = []

    question = item.get("question")
    if isinstance(question, str) and question.strip():
        lines.append(f"Question: {question.strip()}")

    options = item.get("options")
    if isinstance(options, list):
        option_lines: list[str] = []
        for option in options:
            if not isinstance(option, dict):
                continue
            label = option.get("option")
            text = option.get("text")
            if isinstance(label, str) and isinstance(text, str):
                option_lines.append(f"{label.strip()}. {text.strip()}")
        if option_lines:
            lines.append("Options:\n" + "\n".join(option_lines))

    correct_answer = item.get("correct_answer")
    if isinstance(correct_answer, str) and correct_answer.strip():
        lines.append(f"Correct answer: {correct_answer.strip()}")

    explanation = item.get("explanation")
    if isinstance(explanation, str) and explanation.strip():
        lines.append(f"Explanation: {explanation.strip()}")

    evidence_reference = item.get("evidence_reference")
    if isinstance(evidence_reference, str) and evidence_reference.strip():
        lines.append(f"Evidence: {evidence_reference.strip()}")

    if lines:
        return "\n\n".join(lines)
    return json.dumps(item, ensure_ascii=False, indent=2)


def _quiz_artefacts_from_result(result) -> list[dict[str, Any]]:
    try:
        parsed = json.loads(result.content)
    except (TypeError, json.JSONDecodeError):
        return [_artifact_from_subagent_result(result)]

    raw_items = parsed.get("quiz_items") if isinstance(parsed, dict) else None
    if raw_items is None and isinstance(parsed, dict) and parsed.get("question"):
        raw_items = [parsed]
    if not isinstance(raw_items, list):
        return [_artifact_from_subagent_result(result)]

    artefacts: list[dict[str, Any]] = []
    for idx, item in enumerate(raw_items, start=1):
        if not isinstance(item, dict):
            continue
        artefacts.append(
            {
                "type": "quiz_item",
                "title": f"Quiz Item {idx}",
                "content": _format_quiz_item_content(item),
                "concept_ids": [],
            }
        )

    return artefacts or [_artifact_from_subagent_result(result)]


def _format_definition_content(item: dict[str, Any]) -> str:
    lines: list[str] = []
    definition = item.get("definition")
    if isinstance(definition, str) and definition.strip():
        lines.append(definition.strip())
    scope = item.get("scope")
    if isinstance(scope, str) and scope.strip():
        lines.append(f"Scope: {scope.strip()}")
    return "\n\n".join(lines) if lines else json.dumps(item, ensure_ascii=False, indent=2)


def _definition_artefacts_from_result(result) -> list[dict[str, Any]]:
    try:
        parsed = json.loads(result.content)
    except (TypeError, json.JSONDecodeError):
        return [_artifact_from_subagent_result(result)]

    raw_items = parsed.get("definitions") if isinstance(parsed, dict) else None
    if raw_items is None and isinstance(parsed, dict) and parsed.get("definition"):
        raw_items = [parsed]
    if not isinstance(raw_items, list):
        return [_artifact_from_subagent_result(result)]

    artefacts: list[dict[str, Any]] = []
    for idx, item in enumerate(raw_items, start=1):
        if not isinstance(item, dict):
            continue
        title = item.get("title")
        if not isinstance(title, str) or not title.strip():
            title = f"Definition {idx}"
        artefacts.append(
            {
                "type": "definition",
                "title": title.strip(),
                "content": _format_definition_content(item),
                "concept_ids": [],
            }
        )

    return artefacts or [_artifact_from_subagent_result(result)]


def _format_concept_content(item: dict[str, Any]) -> str:
    lines: list[str] = []
    explanation = item.get("explanation")
    if isinstance(explanation, str) and explanation.strip():
        lines.append(explanation.strip())
    relationships = item.get("relationships")
    if isinstance(relationships, str) and relationships.strip():
        lines.append(f"Relationships: {relationships.strip()}")
    example = item.get("example")
    if isinstance(example, str) and example.strip():
        lines.append(f"Example: {example.strip()}")
    return "\n\n".join(lines) if lines else json.dumps(item, ensure_ascii=False, indent=2)


def _concept_artefacts_from_result(result) -> list[dict[str, Any]]:
    try:
        parsed = json.loads(result.content)
    except (TypeError, json.JSONDecodeError):
        return [_artifact_from_subagent_result(result)]

    raw_items = parsed.get("concepts") if isinstance(parsed, dict) else None
    if raw_items is None and isinstance(parsed, dict) and parsed.get("explanation"):
        raw_items = [parsed]
    if not isinstance(raw_items, list):
        return [_artifact_from_subagent_result(result)]

    artefacts: list[dict[str, Any]] = []
    for idx, item in enumerate(raw_items, start=1):
        if not isinstance(item, dict):
            continue
        title = item.get("title")
        if not isinstance(title, str) or not title.strip():
            title = f"Concept {idx}"
        artefacts.append(
            {
                "type": "concept",
                "title": title.strip(),
                "content": _format_concept_content(item),
                "concept_ids": [],
            }
        )

    return artefacts or [_artifact_from_subagent_result(result)]


def _artefacts_from_subagent_result(result) -> list[dict[str, Any]]:
    if result.artifact_type.value == "definition":
        return _definition_artefacts_from_result(result)
    if result.artifact_type.value == "concept":
        return _concept_artefacts_from_result(result)
    if result.artifact_type.value == "quiz_item":
        return _quiz_artefacts_from_result(result)
    return [_artifact_from_subagent_result(result)]


def _generate_subagent_artefacts(
    *,
    artifact_generation_plan: dict[str, Any],
    user_input: str,
    retrieved_chunks: list[dict[str, Any]],
    session_id: str,
    existing_artefacts: list[dict[str, Any]],
    backend: Any,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, str]]]:
    generated_artefacts: list[dict[str, Any]] = []
    generated_debug: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []

    artifacts_needed = artifact_generation_plan.get("artifacts_needed", [])
    if not isinstance(artifacts_needed, list):
        return generated_artefacts, generated_debug, errors

    target_audience = artifact_generation_plan.get("target_audience", "general")
    if not isinstance(target_audience, str) or not target_audience.strip():
        target_audience = "general"

    for artifact_type in artifacts_needed:
        try:
            request = _subagent_request(
                artifact_type=str(artifact_type),
                user_input=user_input,
                retrieved_chunks=retrieved_chunks,
                session_id=session_id,
                related_artifacts=existing_artefacts + generated_artefacts,
                target_audience=target_audience,
            )
            subagent_id = subagent_coordinator.spawn_subagent(request.artifact_type.value, request)
            result = subagent_coordinator.execute_subagent(subagent_id, backend)
            artefacts = _artefacts_from_subagent_result(result)
            generated_artefacts.extend(artefacts)
            for artefact in artefacts:
                generated_debug.append(
                    {
                        "type": artefact["type"],
                        "title": artefact["title"],
                        "confidence": result.confidence,
                        "metadata": result.metadata,
                    }
                )
        except Exception as exc:
            errors.append(
                {
                    "type": str(artifact_type),
                    "error": str(exc),
                }
            )

    return generated_artefacts, generated_debug, errors


def _plan_for_missing_artifacts(
    artifact_generation_plan: dict[str, Any],
    missing_artifact_types: list[str],
) -> dict[str, Any]:
    return {
        **artifact_generation_plan,
        "artifacts_needed": missing_artifact_types,
    }


def _desired_artifact_counts(
    artifact_types: list[str],
    context: str,
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for artifact_type in artifact_types:
        if artifact_type == "definition":
            counts[artifact_type] = estimate_definition_count(context)
        elif artifact_type == "concept":
            counts[artifact_type] = estimate_concept_count(context)
        elif artifact_type == "quiz_item":
            counts[artifact_type] = estimate_quiz_item_count(context)
        else:
            counts[artifact_type] = 1
    return counts


def store_session_history(
    *,
    session_id: str,
    user_id: str | None = None,
    user_input: str,
    router_classification: Any,
    generated_artefacts: list[str],
    citations_used: list[str],
    db_provider: Any | None = None,
) -> None:
    existing_title: str | None = None
    with get_conn() as conn:
        row = conn.execute(
            "SELECT session_title FROM session_history WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        if row is not None:
            existing_title = row["session_title"]

        session_title = existing_title or build_session_title(user_input)
        conn.execute(
            """
            INSERT OR REPLACE INTO session_history(
                session_id, user_id, session_title, timestamp,
                router_classification, user_query, generated_artefacts,
                citations_used, user_feedback, session_embedding
            ) VALUES (?, ?, ?, datetime('now'), ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                user_id,
                session_title,
                json.dumps(_route_as_dict(router_classification), ensure_ascii=False),
                user_input,
                json.dumps(generated_artefacts, ensure_ascii=False),
                json.dumps(citations_used, ensure_ascii=False),
                json.dumps({}, ensure_ascii=False),
                None,
            ),
        )


def handle_turn(
    *,
    session_id: str,
    user_input: str,
    user_id: str | None = None,
    collection_name: str | None = None,
    chat_history: list[dict[str, str]] | None = None,
    model_override: str | None = None,
) -> dict[str, Any]:
    init_db()
    create_session(session_id)

    collection = _collection_for_user(collection_name, user_id)
    router_backend = create_chat_backend()
    route = route_with_agent(
        router_backend,
        user_input=user_input,
        chat_history=chat_history,
        session_ctx={"session_id": session_id, "user_id": user_id},
        model_override=model_override,
    )

    retrieval = run_retrieval(
        query=user_input,
        collection_name=collection,
        k_retrieve=30,
        k_final=8,
    )

    session_ctx = {
        "session_id": session_id,
        "detected_themes": getattr(route, "detected_themes", []),
        "knowledge_gaps": getattr(route, "knowledge_gaps", []),
        "related_sessions": getattr(route, "related_sessions", []),
    }
    if user_id:
        session_ctx["user_id"] = user_id

    state = decide_state(
        route.role,
        retrieval["confidence"],
        session_ctx,
        False,
    )

    model_selection = getattr(route, "model_selection", None) or model_selection_for_role(route.role)
    # Use model override if provided, otherwise use the model from selection
    model_name_to_use = model_override if model_override is not None else model_selection.get("model_name")
    backend = create_chat_backend(model_name_to_use)
    client = LLMClient(backend)
    prompt = build_prompt(
        user_input=user_input,
        role=route.role,
        role_instructions=get_role_prompt(route.role),
        state=state,
        retrieved_chunks=retrieval["chunks"],
        intent=route.reason,
        distance=route.distance,
        knowledge_mode=route.knowledge_mode,
        confidence=retrieval["confidence"],
        chat_history=chat_history,
        session_ctx=session_ctx,
    )

    payload = client.generate_json(
        prompt,
        fallback_role=route.role,
        fallback_state=state,
        fallback_intent=route.reason,
        fallback_distance=route.distance,
        fallback_confidence=retrieval["confidence"],
        fallback_retrieval_count=len(retrieval["chunks"]),
    )

    payload["telemetry"]["intent"] = route.reason
    payload["telemetry"]["distance"] = route.distance
    payload["telemetry"]["confidence"] = retrieval["confidence"]
    payload["telemetry"]["retrieval_count"] = len(retrieval["chunks"])
    artifact_generation_plan = normalize_artifact_generation_plan(
        getattr(route, "artifact_generation_plan", {}),
        user_input=user_input,
    )
    artifact_context = _artifact_context(user_input, retrieval["chunks"])
    desired_artifact_counts = _desired_artifact_counts(
        artifact_generation_plan.get("artifacts_needed", []),
        artifact_context,
    )
    reuse_decision = artifact_reuse_agent.find_reusable_artifacts(
        project=collection,
        user_input=user_input,
        artifact_types=artifact_generation_plan.get("artifacts_needed", []),
        desired_counts=desired_artifact_counts,
    )
    reused_artefacts = [
        _artifact_from_stored(artifact)
        for artifact in reuse_decision.reused_artifacts
    ]
    reused_artifact_fingerprints = {
        _artifact_fingerprint(_strip_internal_artifact_fields(artifact))
        for artifact in reused_artefacts
    }
    generation_plan = _plan_for_missing_artifacts(
        artifact_generation_plan,
        reuse_decision.missing_artifact_types,
    )
    (
        generated_subagent_artefacts,
        generated_artifacts_debug,
        artifact_generation_errors,
    ) = _generate_subagent_artefacts(
        artifact_generation_plan=generation_plan,
        user_input=user_input,
        retrieved_chunks=retrieval["chunks"],
        session_id=session_id,
        existing_artefacts=payload.get("artefacts", []) + reused_artefacts,
        backend=backend,
    )
    payload["artefacts"] = [
        _strip_internal_artifact_fields(artefact)
        for artefact in payload.get("artefacts", []) + reused_artefacts + generated_subagent_artefacts
    ]
    payload["router_debug"] = {
        "role": route.role,
        "knowledge_mode": route.knowledge_mode,
        "distance": route.distance,
        "model_name": model_selection.get("model_name") or "",
        "model_reason": model_selection.get("reason") or "",
        "routing_confidence": route.routing_confidence,
        "reason": route.reason,
        "required_context": route.required_context,
        "verification_need": route.verification_need,
        "next_state": route.next_state,
        "used_fallback": route.used_fallback,
        "detected_themes": getattr(route, "detected_themes", []),
        "knowledge_gaps": getattr(route, "knowledge_gaps", []),
        "related_sessions": getattr(route, "related_sessions", []),
        "artifact_generation_plan": artifact_generation_plan,
        "generated_artifacts": generated_artifacts_debug,
        "reused_artifacts": [
            {
                "id": artifact.get("id"),
                "type": artifact.get("type"),
                "title": artifact.get("title"),
            }
            for artifact in reuse_decision.reused_artifacts
        ],
        "desired_artifact_counts": desired_artifact_counts,
        "artifact_generation_errors": artifact_generation_errors,
    }
    payload["citations"] = merge_citations(payload.get("citations", []), retrieval["chunks"])

    validated = AssistantPayload.model_validate(payload)
    payload = validated.model_dump()

    turn = TurnRecord(
        session_id=session_id,
        user_id=user_id,
        user_input=user_input,
        intent=route.reason,
        distance=route.distance,
        role=payload["role"],
        state=payload["state"],
        confidence=retrieval["confidence"],
        llm_json=json.dumps(payload, ensure_ascii=False),
        system_state=json.dumps(
            {
                "role": payload["role"],
                "state": payload["state"],
                "intent": route.reason,
                "distance": route.distance,
                "confidence": retrieval["confidence"],
            },
            ensure_ascii=False,
        ),
    )
    log_turn(turn)

    generated_artefacts = [artefact["title"] for artefact in payload["artefacts"]]
    citations_used = [citation["chunk_id"] for citation in payload["citations"]]
    store_session_history(
        session_id=session_id,
        user_id=user_id,
        user_input=user_input,
        router_classification=route,
        generated_artefacts=generated_artefacts,
        citations_used=citations_used,
    )

    new_artefacts = [
        artefact
        for artefact in payload["artefacts"]
        if _artifact_fingerprint(artefact) not in reused_artifact_fingerprints
    ]
    if new_artefacts:
        refs = [
            {"ref_type": "chunk", "ref_id": chunk["chunk_id"]}
            for chunk in retrieval["chunks"][:5]
        ]
        save_artefacts(new_artefacts, project=collection, refs=refs)

    return payload


def orchestrate(
    *,
    user_input: str,
    session_id: str,
    user_id: str,
    chat_history: list[dict[str, str]] | None = None,
    db_provider: Any | None = None,
    collection_name: str = "default",
    backend: Any | None = None,
    router_backend: Any | None = None,
    session_ctx: dict | None = None,
    model_override: str | None = None,
) -> dict[str, Any]:
    return handle_turn(
        session_id=session_id,
        user_id=user_id,
        user_input=user_input,
        collection_name=collection_name,
        chat_history=chat_history,
        model_override=model_override,
    )
