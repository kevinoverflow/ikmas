import json
from typing import Any

from app.domain.schema import AssistantPayload

def validate_payload(data: dict) -> AssistantPayload:
    """
    Validate a Python dict against the AssistantPayload schema.

    Raises:
        ValidationError if the data does not match the schema.
    """
    return AssistantPayload.model_validate(data)


def parse_and_validate_json(raw_text: str) -> AssistantPayload:
    """
    Parse raw LLM output (string) into JSON and validate it.

    Steps:
    1. Parse JSON string → dict
    2. Validate against schema

    Raises:
        json.JSONDecodeError if invalid JSON
        ValidationError if schema mismatch
    """
    obj = json.loads(raw_text)
    return validate_payload(obj)


def fallback_payload(
    role: str = "TutoringAgent",
    state: str | None = "ASSESS",
    intent: str = "learn_mode",
    distance: str = "ESN",
    confidence: float = 0.0,
) -> dict[str, Any]:
    """
    Generate a deterministic fallback response if LLM output is invalid.

    This ensures the system never returns an unusable response.

    Typically triggered when:
    - JSON parsing fails
    - schema validation fails
    - repair attempt also fails
    """
    return {
        "role": role,
        "state": state,
        "assistant_message": (
            "Ich bin noch nicht sicher, worauf du genau hinauswillst. "
            "Lass uns das kurz eingrenzen."
        ),
        "questions": [
            {
                "id": "q1",
                "type": "text",
                "label": "Welches Thema oder Konzept meinst du genau?",
                "options": [],
                "required": True,
            },
            {
                "id": "q2",
                "type": "text",
                "label": (
                    "Möchtest du eher eine einfache Erklärung, "
                    "Anwendung oder Übungsfragen?"
                ),
                "options": [],
                "required": True,
            },
        ],
        "artefacts": [],
        "actions": [
            {
                "type": "ask",
                "payload": {},
            }
        ],
        "citations": [],
        "telemetry": {
            "intent": intent,
            "distance": distance,
            "confidence": confidence,
            "retrieval_count": 0,
            "repair_used": False,
            "fallback_used": True,
        },
    }