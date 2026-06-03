import pytest

from app.backend.router_agent import build_router_prompt, route_with_agent


def test_build_router_prompt_includes_registry_and_user_request():
    prompt = build_router_prompt(
        "Erstelle aus unseren Notizen eine Doku.",
        [{"user": "Hallo", "assistant": "Hi"}],
        session_insights={
            "recurring_themes": ["EXTERNALIZATION"],
            "related_sessions": [{"title": "Old notes", "query": "Make a decision record"}],
        },
    )

    assert '"agent": "ScribeAgent"' in prompt
    assert "Erstelle aus unseren Notizen eine Doku." in prompt
    assert "User: Hallo" in prompt
    assert '"allowed_values"' in prompt
    assert '"routing_confidence": [' in prompt
    assert "EXTERNALIZATION" in prompt
    assert "Old notes" in prompt


def test_route_with_agent_uses_llm_router_output():
    class FakeBackend:
        def generate(self, prompt, **kwargs):
            return """{
              "seci_mode": "Externalization",
              "reuse_situation": "Shared Work Producer",
              "selected_agent": "ScribeAgent",
              "routing_confidence": "high",
              "reason": "The user wants reusable documentation from fragmented work traces.",
              "required_context": ["raw notes", "target audience"],
              "verification_need": "user confirmation of completeness",
              "next_state": "agent_execution"
            }"""

    decision = route_with_agent(
        FakeBackend(),
        user_input="Mach aus unseren Stichpunkten eine saubere Doku.",
        chat_history=[],
        session_ctx={},
    )

    assert decision.role == "ScribeAgent"
    assert decision.knowledge_mode == "EXTERNALIZATION"
    assert decision.distance == "SWP"
    assert decision.used_fallback is False
    assert decision.model_selection["model_name"]
    assert "SCRIBE_MODEL_NAME" in decision.model_selection["reason"]


def test_route_with_agent_accepts_numeric_confidence_and_scalar_context_fields():
    class FakeBackend:
        def generate(self, prompt, **kwargs):
            return """{
              "seci_mode": "Externalization",
              "reuse_situation": "Expertise-Seeking Novice",
              "selected_agent": "MentorAgent",
              "routing_confidence": 0.95,
              "reason": "The request indicates a need to understand expert knowledge outside the user's current expertise.",
              "required_context": "Basic understanding of psychology or cognitive science terms.",
              "verification_need": false,
              "next_state": "MentorAgent engaged for explanation"
            }"""

    decision = route_with_agent(
        FakeBackend(),
        user_input="Was ist Cognitive Load?",
        chat_history=[],
        session_ctx={},
    )

    assert decision.role == "MentorAgent"
    assert decision.knowledge_mode == "EXTERNALIZATION"
    assert decision.distance == "ESN"
    assert decision.routing_confidence == "high"
    assert decision.required_context == ["Basic understanding of psychology or cognitive science terms."]
    assert decision.verification_need == "none"
    assert decision.next_state == "MentorAgent engaged for explanation"
    assert decision.used_fallback is False


def test_route_with_agent_ignores_router_model_selection_field():
    class FakeBackend:
        def generate(self, prompt, **kwargs):
            return """{
              "seci_mode": "Combination",
              "reuse_situation": "Secondary Knowledge Miner",
              "selected_agent": "ContextReconstructorAgent",
              "routing_confidence": "high",
              "reason": "The user wants to reuse an artifact from another context.",
              "required_context": [],
              "verification_need": "none",
              "next_state": "agent_execution",
              "model_selection": {
                "model_name": "not-a-real-agent-model",
                "temperature": 0.9
              }
            }"""

    decision = route_with_agent(
        FakeBackend(),
        user_input="Can I reuse this old policy for a different department?",
        chat_history=[],
        session_ctx={},
    )

    assert decision.role == "ContextReconstructorAgent"
    assert decision.used_fallback is False
    assert decision.model_selection["model_name"] != "not-a-real-agent-model"


def test_route_with_agent_raises_on_invalid_router_output():
    class FakeBackend:
        def generate(self, prompt, **kwargs):
            return "kein json"

    with pytest.raises(Exception):
        route_with_agent(
            FakeBackend(),
            user_input="Erkläre mir das Thema einfach.",
            chat_history=[],
            session_ctx={},
        )


def test_route_with_agent_accepts_json_inside_markdown_fence():
    class FakeBackend:
        def generate(self, prompt, **kwargs):
            return """```json
            {
              "seci_mode": "Combination",
              "reuse_situation": "Secondary Knowledge Miner",
              "selected_agent": "Context Reconstructor Agent",
              "routing_confidence": "high",
              "reason": "The user wants transfer conditions for an old artefact.",
              "required_context": [],
              "verification_need": "none",
              "next_state": "agent_execution"
            }
            ```"""

    decision = route_with_agent(
        FakeBackend(),
        user_input="Can this old onboarding doc be reused in another team?",
        chat_history=[],
        session_ctx={},
    )

    assert decision.role == "ContextReconstructorAgent"
    assert decision.used_fallback is False


def test_route_with_agent_adds_session_insights_to_prompt_and_decision(monkeypatch):
    seen = {}

    def fake_history(user_id, query_embedding=None, since_days=30, current_session_id=None):
        seen["history_args"] = (user_id, since_days, current_session_id)
        return {
            "recurring_themes": ["ScribeAgent", "EXTERNALIZATION"],
            "uncaptured_themes": ["decision rationale"],
            "related_sessions": [
                {
                    "session_id": "old-session",
                    "title": "Architecture notes",
                    "query": "Turn notes into ADR",
                    "generated_artefacts": ["ADR"],
                    "citations_used": [],
                }
            ],
        }

    class FakeBackend:
        def generate(self, prompt, **kwargs):
            seen["prompt"] = prompt
            return """{
              "seci_mode": "Externalization",
              "reuse_situation": "Shared Work Producer",
              "selected_agent": "ScribeAgent",
              "routing_confidence": "high",
              "reason": "The user wants reusable documentation.",
              "required_context": [],
              "verification_need": "none",
              "next_state": "agent_execution"
            }"""

    monkeypatch.setattr("app.backend.router_agent.get_relevant_history", fake_history)

    decision = route_with_agent(
        FakeBackend(),
        user_input="Please document this decision.",
        chat_history=[],
        session_ctx={"user_id": "user-1", "session_id": "current-session"},
    )

    assert seen["history_args"] == ("user-1", 30, "current-session")
    assert "Architecture notes" in seen["prompt"]
    assert decision.detected_themes == ["ScribeAgent", "EXTERNALIZATION"]
    assert decision.knowledge_gaps == ["decision rationale"]
    assert decision.related_sessions[0]["session_id"] == "old-session"
