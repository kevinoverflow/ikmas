import pytest

from app.backend.schema import SchemaValidationError, fallback_payload, validate_assistant_payload


def _valid_payload(role="TutoringAgent", state="ASSESS", mode="assistant_response", phase="ASSISTANT"):
    return {
        "mode": mode,
        "interaction_phase": phase,
        "role": role,
        "state": state,
        "assistant_message": "msg",
        "questions": [
            {
                "id": "q1",
                "type": "single_choice",
                "prompt": "p",
                "options": ["a", "b"],
            }
        ],
        "artefacts": [
            {
                "type": "summary",
                "title": "t",
                "body_md": "body",
            }
        ],
        "actions": [{"type": "RETRIEVE", "query": "q", "filters": {"project": "default"}}],
        "citations": [{"source_id": "doc#1", "score": 0.5}],
        "telemetry": {"confidence": 0.5, "needs_followup": True},
    }


def test_validate_payload_ok():
    payload = _valid_payload()
    validate_assistant_payload(payload)


def test_validate_payload_rejects_state_for_non_tutor():
    payload = _valid_payload(role="MentorAgent", state="ASSESS")
    with pytest.raises(SchemaValidationError):
        validate_assistant_payload(payload)


def test_validate_payload_rejects_mode_phase_mismatch():
    payload = _valid_payload(mode="role_clarification", phase="ASSISTANT")
    with pytest.raises(SchemaValidationError):
        validate_assistant_payload(payload)


def test_fallback_payload_is_schema_valid():
    payload = fallback_payload(role="MentorAgent", state=None, confidence=0.2)
    validate_assistant_payload(payload)
