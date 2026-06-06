import pytest
from pydantic import ValidationError

from app.domain.schema import AssistantPayload, Question


def make_valid_payload():
    return {
        "role": "MentorAgent",
        "state": None,
        "assistant_message": "Here is the explanation.",
        "questions": [
            {
                "id": "q1",
                "type": "single_choice",
                "label": "Which answer fits?",
                "options": ["A", "B"],
                "required": True,
            }
        ],
        "artefacts": [
            {
                "type": "summary",
                "title": "Short recap",
                "content": "Important concepts",
                "concept_ids": [1, 2],
            }
        ],
        "actions": [
            {
                "type": "ask",
                "payload": {"follow_up": "Tell me more"},
            }
        ],
        "citations": [
            {
                "source": "chapter1.pdf",
                "chunk_id": "chunk-1",
                "title": "Chapter 1",
                "locator": "p. 3",
            }
        ],
        "telemetry": {
            "intent": "simplify",
            "distance": "ESN",
            "confidence": 0.92,
            "retrieval_count": 3,
            "repair_used": False,
            "fallback_used": False,
        },
        "router_debug": {
            "role": "MentorAgent",
            "knowledge_mode": "SOCIALIZATION",
            "distance": "ESN",
            "model_name": "Qwen/Qwen3-Coder-30B-A3B-Instruct",
            "model_reason": "Chosen from MENTOR_MODEL_NAME because the selected role explains expert knowledge for a novice audience.",
            "routing_confidence": "high",
            "reason": "The user needs accessible explanation.",
            "required_context": ["document excerpt"],
            "verification_need": "none",
            "next_state": "agent_execution",
            "used_fallback": False,
        },
    }


def test_assistant_payload_accepts_valid_nested_schema():
    payload = AssistantPayload.model_validate(make_valid_payload())

    assert payload.role == "MentorAgent"
    assert payload.state is None
    assert payload.questions[0].options == ["A", "B"]
    assert payload.artefacts[0].concept_ids == [1, 2]
    assert payload.actions[0].payload["follow_up"] == "Tell me more"
    assert payload.telemetry.retrieval_count == 3
    assert payload.router_debug is not None
    assert payload.router_debug.role == "MentorAgent"


def test_assistant_payload_rejects_extra_top_level_fields():
    payload = make_valid_payload()
    payload["unexpected"] = "nope"

    with pytest.raises(ValidationError) as excinfo:
        AssistantPayload.model_validate(payload)

    assert excinfo.value.errors()[0]["loc"] == ("unexpected",)


def test_assistant_payload_rejects_extra_nested_fields():
    payload = make_valid_payload()
    payload["questions"][0]["extra"] = "nope"

    with pytest.raises(ValidationError) as excinfo:
        AssistantPayload.model_validate(payload)

    assert excinfo.value.errors()[0]["loc"] == ("questions", 0, "extra")


def test_question_defaults_optional_fields():
    question = Question.model_validate(
        {
            "id": "q2",
            "type": "text",
            "label": "Explain the concept.",
        }
    )

    assert question.options == []
    assert question.required is True


def test_assistant_payload_accepts_subagent_artifact_types():
    payload = make_valid_payload()
    payload["artefacts"] = [
        {"type": "definition", "title": "Definition", "content": "A precise meaning.", "concept_ids": []},
        {"type": "concept", "title": "Concept", "content": "A conceptual explanation.", "concept_ids": []},
        {"type": "quiz_item", "title": "Quiz Item", "content": "Question and answer.", "concept_ids": []},
    ]

    validated = AssistantPayload.model_validate(payload)

    assert [artifact.type for artifact in validated.artefacts] == [
        "definition",
        "concept",
        "quiz_item",
    ]
