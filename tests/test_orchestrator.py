import json
from types import SimpleNamespace

from app.backend import orchestrator
from app.backend import sqlite_store
from app.prompts.prompts import get_role_prompt


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

    def fake_route_with_agent(backend, *, user_input, chat_history=None, session_ctx=None):
        seen["route_args"] = (backend, user_input, chat_history, session_ctx)
        return SimpleNamespace(
            role="MentorAgent",
            knowledge_mode="SOCIALIZATION",
            distance="ESN",
            routing_confidence="high",
            reason="novice explanation",
            required_context=[],
            verification_need="none",
            next_state="agent_execution",
            used_fallback=False,
            detected_themes=["MentorAgent"],
            knowledge_gaps=["retrieval basics"],
            related_sessions=[
                {
                    "session_id": "older-session",
                    "title": "Retrieval intro",
                    "query": "Explain RAG",
                    "generated_artefacts": ["Glossary"],
                }
            ],
        )

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
    monkeypatch.setattr(orchestrator, "route_with_agent", fake_route_with_agent)
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
    assert seen["route_args"][1] == "Erkläre bitte Retrieval"
    assert seen["route_args"][2] == [{"user": "Hallo", "assistant": "Hi"}]
    assert seen["route_args"][3]["session_id"] == "session-123"
    assert seen["state_args"] == (
        "MentorAgent",
        0.88,
        {
            "session_id": "session-123",
            "detected_themes": ["MentorAgent"],
            "knowledge_gaps": ["retrieval basics"],
            "related_sessions": [
                {
                    "session_id": "older-session",
                    "title": "Retrieval intro",
                    "query": "Explain RAG",
                    "generated_artefacts": ["Glossary"],
                }
            ],
        },
        False,
    )
    assert seen["fallback_kwargs"]["fallback_role"] == "MentorAgent"
    assert seen["fallback_kwargs"]["fallback_state"] is None
    assert "Nutzer: Hallo" in seen["prompt"]
    assert "knowledge_mode: SOCIALIZATION" in seen["prompt"]
    assert "Session Context:" in seen["prompt"]
    assert "Retrieval intro" in seen["prompt"]
    assert "retrieval basics" in seen["prompt"]
    assert "Rollenanweisung:" in seen["prompt"]
    assert get_role_prompt("MentorAgent") in seen["prompt"]
    assert payload["router_debug"]["role"] == "MentorAgent"
    assert payload["router_debug"]["knowledge_mode"] == "SOCIALIZATION"
    assert payload["router_debug"]["model_name"]
    assert payload["router_debug"]["model_reason"]
    assert payload["router_debug"]["used_fallback"] is False
    assert payload["router_debug"]["detected_themes"] == ["MentorAgent"]
    assert payload["router_debug"]["knowledge_gaps"] == ["retrieval basics"]
    assert payload["router_debug"]["related_sessions"][0]["title"] == "Retrieval intro"
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
    monkeypatch.setattr(
        orchestrator,
        "route_with_agent",
        lambda *args, **kwargs: SimpleNamespace(
            role="ContextReconstructorAgent",
            knowledge_mode="INTERNALIZATION",
            distance="SKM",
            routing_confidence="high",
            reason="missing context",
            required_context=[],
            verification_need="none",
            next_state="agent_execution",
            used_fallback=False,
        ),
    )
    monkeypatch.setattr(orchestrator, "decide_state", lambda *args, **kwargs: None)
    monkeypatch.setattr(orchestrator, "OpenAIChatBackend", lambda: object())
    monkeypatch.setattr(orchestrator, "log_turn", lambda turn: None)

    class FakeLLMClient:
        def __init__(self, backend):
            self.backend = backend

        def generate_json(self, prompt, **kwargs):
            return make_valid_payload(
                role="ContextReconstructorAgent",
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


def test_handle_turn_appends_subagent_artifacts_and_persists_combined_artefacts(monkeypatch):
    seen = {}

    monkeypatch.setattr(orchestrator, "init_db", lambda: None)
    monkeypatch.setattr(orchestrator, "create_session", lambda session_id: None)
    monkeypatch.setattr(orchestrator, "run_retrieval", lambda **kwargs: {
        "chunks": [],
        "top1": 0.0,
        "avg_top3": 0.0,
        "coverage": 0.0,
        "confidence": 0.0,
    })
    monkeypatch.setattr(
        orchestrator,
        "route_with_agent",
        lambda *args, **kwargs: SimpleNamespace(
            role="MentorAgent",
            knowledge_mode="INTERNALIZATION",
            distance="ESN",
            routing_confidence="high",
            reason="learning support",
            required_context=[],
            verification_need="none",
            next_state="agent_execution",
            used_fallback=False,
            artifact_generation_plan={
                "artifacts_needed": ["definition"],
                "target_audience": "novice",
                "reason": "Definition requested.",
            },
        ),
    )
    monkeypatch.setattr(orchestrator, "decide_state", lambda *args, **kwargs: None)
    monkeypatch.setattr(orchestrator, "OpenAIChatBackend", lambda: object())
    monkeypatch.setattr(orchestrator, "log_turn", lambda turn: None)
    monkeypatch.setattr(orchestrator, "store_session_history", lambda **kwargs: seen.setdefault("history", kwargs))

    class FakeLLMClient:
        def __init__(self, backend):
            self.backend = backend

        def generate_json(self, prompt, **kwargs):
            return make_valid_payload(
                artefacts=[
                    {
                        "type": "summary",
                        "title": "Main Recap",
                        "content": "Main agent artifact",
                        "concept_ids": [],
                    }
                ]
            )

    class FakeCoordinator:
        def spawn_subagent(self, agent_type, request):
            seen["request"] = request
            return "subagent-1"

        def execute_subagent(self, subagent_id, backend):
            return SimpleNamespace(
                artifact_type=SimpleNamespace(value="definition"),
                content="Generated definition",
                metadata={"audience_level": "novice"},
                confidence=0.9,
            )

    def fake_save_artefacts(artefacts, project, refs):
        seen["saved_artefacts"] = artefacts
        seen["project"] = project
        return [1, 2]

    monkeypatch.setattr(orchestrator, "LLMClient", FakeLLMClient)
    monkeypatch.setattr(orchestrator, "subagent_coordinator", FakeCoordinator())
    monkeypatch.setattr(orchestrator, "save_artefacts", fake_save_artefacts)

    payload = orchestrator.handle_turn(
        session_id="session-artifacts",
        user_input="Bitte gib mir eine Definition.",
        collection_name="team-space",
    )

    assert [artefact["type"] for artefact in payload["artefacts"]] == ["summary", "definition"]
    assert payload["artefacts"][1]["title"] == "Definition"
    assert payload["artefacts"][1]["content"] == "Generated definition"
    assert payload["router_debug"]["generated_artifacts"][0]["type"] == "definition"
    assert payload["router_debug"]["artifact_generation_errors"] == []
    assert seen["request"].target_audience == "novice"
    assert [artefact["title"] for artefact in seen["saved_artefacts"]] == ["Main Recap", "Definition"]
    assert seen["history"]["generated_artefacts"] == ["Main Recap", "Definition"]
    assert seen["project"] == "team-space"


def test_handle_turn_keeps_main_answer_when_subagent_fails(monkeypatch):
    seen = {}

    monkeypatch.setattr(orchestrator, "init_db", lambda: None)
    monkeypatch.setattr(orchestrator, "create_session", lambda session_id: None)
    monkeypatch.setattr(orchestrator, "run_retrieval", lambda **kwargs: {
        "chunks": [],
        "top1": 0.0,
        "avg_top3": 0.0,
        "coverage": 0.0,
        "confidence": 0.0,
    })
    monkeypatch.setattr(
        orchestrator,
        "route_with_agent",
        lambda *args, **kwargs: SimpleNamespace(
            role="MentorAgent",
            knowledge_mode="INTERNALIZATION",
            distance="ESN",
            routing_confidence="high",
            reason="learning support",
            required_context=[],
            verification_need="none",
            next_state="agent_execution",
            used_fallback=False,
            artifact_generation_plan={
                "artifacts_needed": ["quiz_item"],
                "target_audience": "general",
                "reason": "Quiz requested.",
            },
        ),
    )
    monkeypatch.setattr(orchestrator, "decide_state", lambda *args, **kwargs: None)
    monkeypatch.setattr(orchestrator, "OpenAIChatBackend", lambda: object())
    monkeypatch.setattr(orchestrator, "log_turn", lambda turn: None)
    monkeypatch.setattr(orchestrator, "store_session_history", lambda **kwargs: None)
    monkeypatch.setattr(orchestrator, "save_artefacts", lambda *args, **kwargs: seen.setdefault("saved", True))

    class FakeLLMClient:
        def __init__(self, backend):
            self.backend = backend

        def generate_json(self, prompt, **kwargs):
            return make_valid_payload()

    class FailingCoordinator:
        def spawn_subagent(self, agent_type, request):
            return "subagent-1"

        def execute_subagent(self, subagent_id, backend):
            raise RuntimeError("quiz failed")

    monkeypatch.setattr(orchestrator, "LLMClient", FakeLLMClient)
    monkeypatch.setattr(orchestrator, "subagent_coordinator", FailingCoordinator())

    payload = orchestrator.handle_turn(
        session_id="session-failure",
        user_input="Mach ein Quiz.",
        collection_name="team-space",
    )

    assert payload["assistant_message"] == "Antwort"
    assert payload["artefacts"] == []
    assert payload["router_debug"]["artifact_generation_errors"] == [
        {"type": "quiz_item", "error": "quiz failed"}
    ]
    assert "saved" not in seen


def test_handle_turn_scopes_default_collection_for_authenticated_user(monkeypatch):
    seen = {}

    monkeypatch.setattr(orchestrator, "init_db", lambda: None)
    monkeypatch.setattr(orchestrator, "create_session", lambda session_id: None)
    def fake_run_retrieval(**kwargs):
        seen["retrieval_kwargs"] = kwargs
        return {
            "chunks": [],
            "top1": 0.0,
            "avg_top3": 0.0,
            "coverage": 0.0,
            "confidence": 0.0,
        }

    monkeypatch.setattr(orchestrator, "run_retrieval", fake_run_retrieval)
    monkeypatch.setattr(
        orchestrator,
        "route_with_agent",
        lambda *args, **kwargs: SimpleNamespace(
            role="MentorAgent",
            knowledge_mode="SOCIALIZATION",
            distance="ESN",
            routing_confidence="high",
            reason="novice explanation",
            required_context=[],
            verification_need="none",
            next_state="agent_execution",
            used_fallback=False,
        ),
    )
    monkeypatch.setattr(orchestrator, "decide_state", lambda *args, **kwargs: None)
    monkeypatch.setattr(orchestrator, "OpenAIChatBackend", lambda: object())
    monkeypatch.setattr(orchestrator, "log_turn", lambda turn: None)
    monkeypatch.setattr(orchestrator, "store_session_history", lambda **kwargs: None)

    class FakeLLMClient:
        def __init__(self, backend):
            self.backend = backend

        def generate_json(self, prompt, **kwargs):
            return make_valid_payload()

    monkeypatch.setattr(orchestrator, "LLMClient", FakeLLMClient)

    orchestrator.handle_turn(
        session_id="session-789",
        user_id="user-123",
        user_input="Was steht in meinen Dateien?",
    )

    assert seen["retrieval_kwargs"]["collection_name"] == "u_user-123__default"


def test_build_prompt_allows_general_knowledge_without_retrieval():
    prompt = orchestrator.build_prompt(
        user_input="Analysiere Bitcoin",
        role="SemanticLinkingAgent",
        role_instructions="Synthesize and connect explicit project artefacts across files and themes.",
        state=None,
        retrieved_chunks=[],
        intent="pattern_mining",
        distance="SWP",
        knowledge_mode="COMBINATION",
        confidence=0.71,
        chat_history=[],
        session_ctx={
            "detected_themes": ["SemanticLinkingAgent"],
            "related_sessions": [
                {
                    "title": "Market scan",
                    "query": "Compare adoption themes",
                    "generated_artefacts": ["Theme map"],
                }
            ],
        },
    )

    assert "Wenn kein Retrieval-Kontext vorhanden ist" in prompt
    assert "Analysiere Bitcoin" in prompt
    assert '"role": "SemanticLinkingAgent"' in prompt
    assert "knowledge_mode: COMBINATION" in prompt
    assert "Market scan" in prompt
    assert "Theme map" in prompt
    assert "Synthesize and connect explicit project artefacts across files and themes." in prompt


def test_store_session_history_keeps_first_message_as_title(tmp_path, monkeypatch):
    monkeypatch.setattr(sqlite_store, "DB_PATH", tmp_path / "ikmas.db")
    sqlite_store.init_db()

    orchestrator.store_session_history(
        session_id="session-title",
        user_id="user-1",
        user_input="Turn notes into decision record",
        router_classification={"role": "ScribeAgent"},
        generated_artefacts=[],
        citations_used=[],
    )
    orchestrator.store_session_history(
        session_id="session-title",
        user_id="user-1",
        user_input="Now make it shorter",
        router_classification={"role": "ScribeAgent"},
        generated_artefacts=[],
        citations_used=[],
    )

    with sqlite_store.get_conn() as conn:
        row = conn.execute(
            """
            SELECT session_title, user_query
            FROM session_history
            WHERE session_id = ?
            """,
            ("session-title",),
        ).fetchone()

    assert row["session_title"] == "Turn notes into decision record"
    assert row["user_query"] == "Now make it shorter"


def test_build_session_title_truncates_long_input():
    title = orchestrator.build_session_title(" ".join(["knowledge"] * 20), max_chars=20)

    assert title == "knowledge knowled..."
    assert len(title) == 20
