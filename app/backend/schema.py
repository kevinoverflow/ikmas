from __future__ import annotations

import json
from typing import Any

from jsonschema import Draft202012Validator, ValidationError

FSM_STATES = ["ASSESS", "EXPLAIN", "CHECK", "PRACTICE", "FEEDBACK", "SCHEDULE"]

ASSISTANT_JSON_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "mode",
        "interaction_phase",
        "role",
        "state",
        "assistant_message",
        "questions",
        "artefacts",
        "actions",
        "citations",
        "telemetry",
    ],
    "properties": {
        "mode": {"type": "string", "enum": ["role_clarification", "assistant_response"]},
        "interaction_phase": {"type": "string", "enum": ["ROLE_GATE", "ASSISTANT"]},
        "role": {"type": "string"},
        "state": {"type": ["string", "null"], "enum": FSM_STATES + [None]},
        "assistant_message": {"type": "string"},
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["id", "type", "prompt", "options"],
                "properties": {
                    "id": {"type": "string"},
                    "type": {"type": "string", "enum": ["single_choice", "multi_choice", "text"]},
                    "prompt": {"type": "string"},
                    "options": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
        "artefacts": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["type", "title", "body_md"],
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": ["decision_record", "case_card", "faq", "sop", "summary", "quiz"],
                    },
                    "title": {"type": "string"},
                    "body_md": {"type": "string"},
                },
            },
        },
        "actions": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["type", "query", "filters"],
                "properties": {
                    "type": {"type": "string"},
                    "query": {"type": "string"},
                    "filters": {"type": "object", "additionalProperties": {"type": ["string", "number", "boolean", "null"]}},
                },
            },
        },
        "citations": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["source_id", "score"],
                "properties": {
                    "source_id": {"type": "string"},
                    "score": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                },
            },
        },
        "telemetry": {
            "type": "object",
            "additionalProperties": False,
            "required": ["confidence", "needs_followup"],
            "properties": {
                "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                "needs_followup": {"type": "boolean"},
            },
        },
    },
}

_VALIDATOR = Draft202012Validator(ASSISTANT_JSON_SCHEMA)


class SchemaValidationError(ValueError):
    pass


def validate_assistant_payload(payload: dict[str, Any]) -> None:
    try:
        _VALIDATOR.validate(payload)
    except ValidationError as exc:
        raise SchemaValidationError(exc.message) from exc

    role = payload.get("role")
    state = payload.get("state")
    if role != "TutoringAgent" and state is not None:
        raise SchemaValidationError("state must be null for non-Tutoring roles")

    mode = payload.get("mode")
    phase = payload.get("interaction_phase")
    if mode == "role_clarification" and phase != "ROLE_GATE":
        raise SchemaValidationError("role_clarification mode requires ROLE_GATE interaction_phase")
    if mode == "assistant_response" and phase != "ASSISTANT":
        raise SchemaValidationError("assistant_response mode requires ASSISTANT interaction_phase")


def validate_or_raise(payload: dict[str, Any]) -> dict[str, Any]:
    validate_assistant_payload(payload)
    return payload


def fallback_payload(
    role: str,
    state: str | None,
    confidence: float,
    project: str = "default",
) -> dict[str, Any]:
    effective_role = role if role in {"TutoringAgent", "MentorAgent", "DigitalMemoryAgent", "ConceptMiningAgent"} else "MentorAgent"
    effective_state = state if effective_role == "TutoringAgent" else None
    if effective_role == "TutoringAgent" and effective_state is None:
        effective_state = "ASSESS"

    payload = {
        "mode": "assistant_response",
        "interaction_phase": "ASSISTANT",
        "role": effective_role,
        "state": effective_state,
        "assistant_message": "Ich benötige noch etwas Kontext, um präzise zu antworten.",
        "questions": [
            {
                "id": "q_scope",
                "type": "single_choice",
                "prompt": "Worauf soll ich mich fokussieren?",
                "options": ["Definition", "Projektanwendung", "Nächster Arbeitsschritt"],
            },
            {
                "id": "q_detail",
                "type": "single_choice",
                "prompt": "Welches Detailniveau passt?",
                "options": ["Kurz", "Mittel", "Detailliert"],
            },
        ],
        "artefacts": [],
        "actions": [{"type": "RETRIEVE", "query": "context clarification", "filters": {"project": project}}],
        "citations": [],
        "telemetry": {"confidence": max(0.0, min(1.0, float(confidence))), "needs_followup": True},
    }
    validate_assistant_payload(payload)
    return payload


def as_schema_json() -> str:
    return json.dumps(ASSISTANT_JSON_SCHEMA, ensure_ascii=True)
