import json

from app.backend import orchestrator


def make_valid_payload(
    *,
    role: str = "MentorAgent",
    state: str | None = None,
    citations: list[dict] | None = None,
    artefacts: list[dict] | None = None,
):
    return {
        "role": role,
        "state": state,
        "assistant_message": "Antwort",
        "questions": [],
        "artefacts": artefacts or [],
        "actions": [
            {
                "type": "ask",
                "payload": {},
            }
        ],
        "citations": citations or [],
        "telemetry": {
            "intent": "what_is",
            "distance": "ESN",
            "confidence": 0.1,
            "retrieval_count": 0,
            "repair_used": False,
            "fallback_used": False,
        },
    }


def test_handle_turn_uses_runtime_pipeline_and_enriches_sources(monkeypatch):
    seen = {}

    def fake_init_db():
        seen["init_db"] = seen.get("init_db", 0) + 1

    def fake_create_session(session_id):
        seen["session_id"] = session_id

    def fake_run_retrieval(query, collection_name, k_retrieve=30, k_final=8):
        seen["retrieval_args"] = (query, collection_name, k_retrieve, k_final)
        return {
            "chunks": [
                {
                    "chunk_id": "chunk-1",
                    "text": "Chunk text",
                    "source": "doc.pdf",
                    "title": "Doc Title",
                    "page": 3,
                    "score": 0.91,
                    "metadata": {},
                }
            ],
            "top1": 0.91,
            "avg_top3": 0.91,
            "coverage": 1.0,
            "confidence": 0.88,
        }

    def fake_role_router(intent, distance, session_ctx):
        seen["role_router_args"] = (intent, distance, session_ctx)
        return "MentorAgent"

    def fake_decide_state(role, retrieval_confidence, session_ctx, force_tutor_mode=False):
        seen["state_args"] = (role, retrieval_confidence, session_ctx, force_tutor_mode)
        return None

    class FakeBackend:
        pass

    class FakeLLMClient:
        def __init__(self, backend):
            seen["backend"] = backend

        def generate_json(self, prompt, **kwargs):
            seen["prompt"] = prompt
            seen["fallback_kwargs"] = kwargs
            return make_valid_payload()

    def fake_log_turn(turn):
        seen["logged_turn"] = turn

    monkeypatch.setattr(orchestrator, "init_db", fake_init_db)
    monkeypatch.setattr(orchestrator, "create_session", fake_create_session)
    monkeypatch.setattr(orchestrator, "run_retrieval", fake_run_retrieval)
    monkeypatch.setattr(orchestrator, "role_router", fake_role_router)
    monkeypatch.setattr(orchestrator, "decide_state", fake_decide_state)
    monkeypatch.setattr(orchestrator, "OpenAIChatBackend", FakeBackend)
    monkeypatch.setattr(orchestrator, "LLMClient", FakeLLMClient)
    monkeypatch.setattr(orchestrator, "log_turn", fake_log_turn)

    payload = orchestrator.handle_turn(
        session_id="session-123",
        user_input="Erkläre bitte Retrieval",
        collection_name="project-a",
        chat_history=[{"user": "Hallo", "assistant": "Hi"}],
    )

    assert seen["init_db"] == 1
    assert seen["session_id"] == "session-123"
    assert seen["retrieval_args"] == ("Erkläre bitte Retrieval", "project-a", 30, 8)
    assert seen["role_router_args"] == ("what_is", "ESN", {})
    assert seen["state_args"] == ("MentorAgent", 0.88, {}, False)
    assert seen["fallback_kwargs"]["fallback_role"] == "MentorAgent"
    assert seen["fallback_kwargs"]["fallback_state"] is None
    assert "Nutzer: Hallo" in seen["prompt"]
    assert payload["telemetry"]["confidence"] == 0.88
    assert payload["telemetry"]["retrieval_count"] == 1
    assert payload["citations"] == [
        {
            "source": "doc.pdf",
            "chunk_id": "chunk-1",
            "title": "Doc Title",
            "locator": "p. 3",
        }
    ]
    assert seen["logged_turn"].role == "MentorAgent"
    assert json.loads(seen["logged_turn"].llm_json)["citations"][0]["chunk_id"] == "chunk-1"


def test_handle_turn_saves_artefacts_in_selected_collection(monkeypatch):
    seen = {}

    monkeypatch.setattr(orchestrator, "init_db", lambda: None)
    monkeypatch.setattr(orchestrator, "create_session", lambda session_id: None)
    monkeypatch.setattr(
        orchestrator,
        "run_retrieval",
        lambda **kwargs: {
            "chunks": [
                {
                    "chunk_id": "chunk-7",
                    "text": "Chunk",
                    "source": "notes.pdf",
                    "title": None,
                    "page": None,
                    "score": 0.5,
                    "metadata": {},
                }
            ],
            "top1": 0.5,
            "avg_top3": 0.5,
            "coverage": 1.0,
            "confidence": 0.5,
        },
    )
    monkeypatch.setattr(orchestrator, "role_router", lambda *args, **kwargs: "DigitalMemoryAgent")
    monkeypatch.setattr(orchestrator, "decide_state", lambda *args, **kwargs: None)
    monkeypatch.setattr(orchestrator, "OpenAIChatBackend", lambda: object())
    monkeypatch.setattr(orchestrator, "log_turn", lambda turn: None)

    class FakeLLMClient:
        def __init__(self, backend):
            self.backend = backend

        def generate_json(self, prompt, **kwargs):
            return make_valid_payload(
                role="DigitalMemoryAgent",
                artefacts=[
                    {
                        "type": "summary",
                        "title": "Recap",
                        "content": "Important notes",
                        "concept_ids": [],
                    }
                ],
            )

    def fake_save_artefacts(artefacts, project, refs):
        seen["artefacts"] = artefacts
        seen["project"] = project
        seen["refs"] = refs
        return [1]

    monkeypatch.setattr(orchestrator, "LLMClient", FakeLLMClient)
    monkeypatch.setattr(orchestrator, "save_artefacts", fake_save_artefacts)

    orchestrator.handle_turn(
        session_id="session-456",
        user_input="Was steht in unseren Dateien?",
        collection_name="team-space",
    )

    assert seen["project"] == "team-space"
    assert seen["artefacts"][0]["title"] == "Recap"
    assert seen["refs"] == [{"ref_type": "chunk", "ref_id": "chunk-7"}]
