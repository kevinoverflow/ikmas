import json

import pytest
from pydantic import ValidationError

from app.backend.validation import fallback_payload, parse_and_validate_json, validate_payload


def make_valid_payload():
    return {
        "role": "TutoringAgent",
        "state": "CHECK",
        "assistant_message": "Antwort",
        "questions": [
            {
                "id": "q1",
                "type": "text",
                "label": "Was mochtest du wissen?",
                "options": [],
                "required": True,
            }
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
            "intent": "learn_mode",
            "distance": "ESN",
            "confidence": 0.75,
            "retrieval_count": 1,
            "repair_used": False,
            "fallback_used": False,
        },
    }


def test_validate_payload_returns_assistant_payload_model():
    payload = validate_payload(make_valid_payload())

    assert payload.role == "TutoringAgent"
    assert payload.state == "CHECK"
    assert payload.telemetry.intent == "learn_mode"


def test_validate_payload_raises_for_schema_mismatch():
    payload = make_valid_payload()
    payload["telemetry"]["unexpected"] = True

    with pytest.raises(ValidationError):
        validate_payload(payload)


def test_parse_and_validate_json_parses_valid_json():
    payload = parse_and_validate_json(json.dumps(make_valid_payload()))

    assert payload.assistant_message == "Antwort"
    assert payload.questions[0].id == "q1"


def test_parse_and_validate_json_raises_for_invalid_json():
    with pytest.raises(json.JSONDecodeError):
        parse_and_validate_json("{invalid json")


def test_fallback_payload_is_schema_valid_and_marks_fallback_usage():
    payload = fallback_payload(
        role="MentorAgent",
        state="FEEDBACK",
        intent="project_specific",
        distance="SWP",
        confidence=0.33,
    )

    validated = validate_payload(payload)

    assert validated.role == "MentorAgent"
    assert validated.state == "FEEDBACK"
    assert validated.telemetry.intent == "project_specific"
    assert validated.telemetry.distance == "SWP"
    assert validated.telemetry.confidence == 0.33
    assert validated.telemetry.fallback_used is True
    assert validated.telemetry.retrieval_count == 0
    assert [question.id for question in validated.questions] == ["q1", "q2"]
