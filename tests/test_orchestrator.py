import json
from types import SimpleNamespace

from app.backend import orchestrator
from app.backend.workflow.planner import WorkflowPlanningDecision
from app.backend.workflow.task_models import TaskPlan, TaskSpec
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
    assert seen["route_args"][1:] == ("Erkläre bitte Retrieval", [{"user": "Hallo", "assistant": "Hi"}], {})
    assert seen["state_args"] == ("MentorAgent", 0.88, {}, False)
    assert seen["fallback_kwargs"]["fallback_role"] == "MentorAgent"
    assert seen["fallback_kwargs"]["fallback_state"] is None
    assert "Nutzer: Hallo" in seen["prompt"]
    assert "knowledge_mode: SOCIALIZATION" in seen["prompt"]
    assert "Rollenanweisung:" in seen["prompt"]
    assert get_role_prompt("MentorAgent") in seen["prompt"]
    assert payload["router_debug"]["role"] == "MentorAgent"
    assert payload["router_debug"]["knowledge_mode"] == "SOCIALIZATION"
    assert payload["router_debug"]["model_name"]
    assert payload["router_debug"]["model_reason"]
    assert payload["router_debug"]["used_fallback"] is False
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
    )

    assert "Wenn kein Retrieval-Kontext vorhanden ist" in prompt
    assert "Analysiere Bitcoin" in prompt
    assert '"role": "SemanticLinkingAgent"' in prompt
    assert "knowledge_mode: COMBINATION" in prompt
    assert "Synthesize and connect explicit project artefacts across files and themes." in prompt


def test_handle_turn_runs_scribe_agentic_workflow(monkeypatch):
    seen = {}

    monkeypatch.setattr(orchestrator, "init_db", lambda: None)
    monkeypatch.setattr(orchestrator, "create_session", lambda session_id: None)
    monkeypatch.setattr(orchestrator, "log_turn", lambda turn: seen.setdefault("turn", turn))
    monkeypatch.setattr(orchestrator, "save_artefacts", lambda **kwargs: None)
    monkeypatch.setattr(orchestrator, "store_session_history", lambda **kwargs: None)
    monkeypatch.setattr(
        orchestrator,
        "run_retrieval",
        lambda **kwargs: {
            "chunks": [],
            "top1": 0.0,
            "avg_top3": 0.0,
            "coverage": 0.0,
            "confidence": 0.2,
        },
    )
    monkeypatch.setattr(
        orchestrator,
        "route_with_agent",
        lambda *args, **kwargs: SimpleNamespace(
            role="ScribeAgent",
            knowledge_mode="EXTERNALIZATION",
            distance="SWP",
            routing_confidence="high",
            reason="meeting notes need structure",
            required_context=[],
            verification_need="none",
            next_state="agent_execution",
            used_fallback=False,
        ),
    )
    monkeypatch.setattr(orchestrator, "decide_state", lambda *args, **kwargs: None)
    monkeypatch.setattr(orchestrator, "OpenAIChatBackend", lambda *args, **kwargs: object())
    monkeypatch.setattr(
        orchestrator,
        "plan_workflow_decision",
        lambda *args, **kwargs: WorkflowPlanningDecision(
            task_plan=TaskPlan(
                should_decompose=True,
                rationale="Planner selected separate Scribe extraction tasks.",
                aggregation_strategy="scribe_knowledge_artifact",
                tasks=[
                    TaskSpec(
                        task_id="t1",
                        task_type="extract_decisions",
                        agent_role="scribe_decision_extractor",
                        input_scope={"section": "decisions"},
                        expected_output_schema="DecisionExtractionResult",
                    ),
                    TaskSpec(
                        task_id="t2",
                        task_type="extract_assumptions",
                        agent_role="scribe_assumption_extractor",
                        input_scope={"section": "assumptions"},
                        expected_output_schema="AssumptionExtractionResult",
                    ),
                    TaskSpec(
                        task_id="t3",
                        task_type="extract_open_issues",
                        agent_role="scribe_issue_extractor",
                        input_scope={"section": "issues"},
                        expected_output_schema="OpenIssueExtractionResult",
                    ),
                ],
            ),
            debug={
                "planning_mode": "multi_agent_planning",
                "selected_plan_source": "workflow_supervisor_agent",
                "steps": [],
            },
        ),
    )

    class FakeLLMClient:
        def __init__(self, backend):
            self.backend = backend

        def generate_json(self, prompt, **kwargs):
            return make_valid_payload(role="ScribeAgent")

    monkeypatch.setattr(orchestrator, "LLMClient", FakeLLMClient)

    payload = orchestrator.handle_turn(
        session_id="scribe-session",
        user_input=(
            "Meeting notes\n"
            "- Decision: use Chroma for vector storage.\n"
            "- Assumption: the SCADS API key is available in production.\n"
            "- Open issue: confirm reranking latency before launch."
        ),
    )

    assert payload["agent_trace"]["total_tasks"] == 3
    assert payload["agent_trace"]["successful_tasks"] == 3
    assert payload["workflow_result"]["decisions"][0]["decision"] == "use Chroma for vector storage."
    assert payload["workflow_result"]["assumptions"][0]["assumption"] == "the SCADS API key is available in production."
    assert payload["workflow_result"]["open_issues"][0]["issue"] == "confirm reranking latency before launch."
    assert payload["workflow_planning_debug"]["planning_mode"] == "multi_agent_planning"
    assert payload["artefacts"][0]["title"] == "Reusable Knowledge Artifact"
    assert "Scribe agentic workflow" in payload["assistant_message"]


def test_handle_turn_generates_flashcard_artefact_from_workflow(monkeypatch):
    monkeypatch.setattr(orchestrator, "init_db", lambda: None)
    monkeypatch.setattr(orchestrator, "create_session", lambda session_id: None)
    monkeypatch.setattr(orchestrator, "log_turn", lambda turn: None)
    monkeypatch.setattr(orchestrator, "store_session_history", lambda **kwargs: None)
    monkeypatch.setattr(
        orchestrator,
        "run_retrieval",
        lambda **kwargs: {
            "chunks": [],
            "top1": 0.0,
            "avg_top3": 0.0,
            "coverage": 0.0,
            "confidence": 0.2,
        },
    )
    monkeypatch.setattr(
        orchestrator,
        "route_with_agent",
        lambda *args, **kwargs: SimpleNamespace(
            role="ScribeAgent",
            knowledge_mode="EXTERNALIZATION",
            distance="SWP",
            routing_confidence="high",
            reason="flashcard artifact generation",
            required_context=[],
            verification_need="none",
            next_state="agent_execution",
            used_fallback=False,
        ),
    )
    monkeypatch.setattr(orchestrator, "decide_state", lambda *args, **kwargs: None)
    monkeypatch.setattr(orchestrator, "OpenAIChatBackend", lambda *args, **kwargs: object())
    monkeypatch.setattr(
        orchestrator,
        "plan_workflow_decision",
        lambda *args, **kwargs: WorkflowPlanningDecision(
            task_plan=TaskPlan(
                should_decompose=True,
                rationale="Planner selected flashcard generation.",
                aggregation_strategy="scribe_knowledge_artifact",
                tasks=[
                    TaskSpec(
                        task_id="t1",
                        task_type="generate_artefact",
                        agent_role="scribe_artifact_generator",
                        input_scope={"section": "flashcards", "artifact_type": "flashcards", "title": "Privatrecht Flashcards"},
                        expected_output_schema="ArtefactGenerationResult",
                    )
                ],
            ),
            debug={"planning_mode": "multi_agent_planning", "validation_status": "accepted_multi_agent"},
        ),
    )

    class FakeLLMClient:
        def __init__(self, backend):
            self.backend = backend

        def generate_json(self, prompt, **kwargs):
            return make_valid_payload(role="ScribeAgent")

    saved = {}
    monkeypatch.setattr(orchestrator, "LLMClient", FakeLLMClient)
    monkeypatch.setattr(orchestrator, "save_artefacts", lambda **kwargs: saved.update(kwargs))

    payload = orchestrator.handle_turn(
        session_id="flashcard-session",
        user_input="Wo sind die Flashcards?",
        chat_history=[
            {
                "user": "## Willenserklärung\n## Vertragsschluss\nGenerate flashcards for all concepts.",
                "assistant": "Hier sind die Flashcards.",
            }
        ],
    )

    assert payload["workflow_result"]["artefacts"]
    assert payload["artefacts"][0]["type"] == "flashcards"
    assert payload["artefacts"][0]["title"] == "Privatrecht Flashcards"
    assert saved["artefacts"][0]["type"] == "flashcards"
