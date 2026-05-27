import json

from app.backend.workflow.planner import plan_workflow, plan_workflow_decision


class FakePlannerBackend:
    def __init__(self, response):
        self.responses = response if isinstance(response, list) else [response]
        self.calls = []

    def generate(self, prompt, **kwargs):
        self.calls.append((prompt, kwargs))
        index = min(len(self.calls) - 1, len(self.responses) - 1)
        return self.responses[index]


def test_plan_workflow_uses_llm_task_plan_for_concept_summaries():
    candidate = {
        "should_decompose": True,
        "rationale": "The request asks for structured summaries across multiple concepts.",
        "aggregation_strategy": "scribe_knowledge_artifact",
        "tasks": [
            {
                "task_id": "t1",
                "task_type": "write_concept_learning_summaries",
                "agent_role": "scribe_concept_summary_writer",
                "input_scope": {"concepts": ["Vertragsrecht", "Sachenrecht"]},
                "expected_output_schema": "ConceptLearningSummaryResult",
                "dependencies": [],
                "priority": 10,
            }
        ],
    }
    backend = FakePlannerBackend(
        [json.dumps(candidate), json.dumps(candidate)]
    )

    plan = plan_workflow(
        backend,
        user_input="Erstelle für jedes Konzept eine Lernzusammenfassung.",
        selected_role="ScribeAgent",
        knowledge_mode="EXTERNALIZATION",
        distance="SWP",
        routing_reason="The user requests structured learning artifacts.",
        retrieved_chunks=[],
    )

    assert plan.should_decompose is True
    assert plan.tasks[0].agent_role == "scribe_concept_summary_writer"
    assert plan.tasks[0].task_type == "write_concept_learning_summaries"
    assert backend.calls[0][1]["response_format"] == {"type": "json_object"}
    assert len(backend.calls) == 2
    assert "Workflow Planner Agent" in backend.calls[0][1]["system_prompt"]
    assert "Workflow Supervisor Agent" in backend.calls[1][1]["system_prompt"]


def test_plan_workflow_falls_back_to_single_agent_on_invalid_worker():
    backend = FakePlannerBackend(
        json.dumps(
            {
                "should_decompose": True,
                "rationale": "Use an unknown worker.",
                "aggregation_strategy": "scribe_knowledge_artifact",
                "tasks": [
                    {
                        "task_id": "t1",
                        "task_type": "invent_task",
                        "agent_role": "invented_worker",
                        "input_scope": {},
                        "expected_output_schema": "InventedResult",
                    }
                ],
            }
        )
    )

    plan = plan_workflow(
        backend,
        user_input="Do something complex.",
        selected_role="ScribeAgent",
        knowledge_mode="EXTERNALIZATION",
        distance="SWP",
        routing_reason="Test",
        retrieved_chunks=[],
    )

    assert plan.should_decompose is False
    assert plan.tasks == []


def test_plan_workflow_debug_exposes_raw_outputs_and_validation_status():
    candidate = {
        "should_decompose": True,
        "rationale": "The request asks for structured summaries across multiple concepts.",
        "aggregation_strategy": "scribe_knowledge_artifact",
        "tasks": [
            {
                "task_id": "t1",
                "task_type": "write_concept_learning_summaries",
                "agent_role": "scribe_concept_summary_writer",
                "input_scope": {"scope": "all concepts"},
                "expected_output_schema": "ConceptLearningSummaryResult",
            }
        ],
    }
    raw = json.dumps(candidate)
    decision = plan_workflow_decision(
        FakePlannerBackend([raw, raw]),
        user_input="Erstelle für jedes Konzept eine Lernzusammenfassung.",
        selected_role="ScribeAgent",
        knowledge_mode="EXTERNALIZATION",
        distance="SWP",
        routing_reason="The user requests structured learning artifacts.",
        retrieved_chunks=[],
    )

    assert decision.task_plan.should_decompose is True
    assert decision.debug["validation_status"] == "accepted_multi_agent"
    assert decision.debug["steps"][0]["raw_output"] == raw
    assert decision.debug["steps"][1]["raw_output"] == raw


def test_plan_workflow_prompt_includes_history_and_missing_parent_artifacts():
    candidate = {
        "should_decompose": True,
        "rationale": "Recover missing flashcard artefact from prior request.",
        "aggregation_strategy": "scribe_knowledge_artifact",
        "tasks": [
            {
                "task_id": "t1",
                "task_type": "generate_artefact",
                "agent_role": "scribe_artifact_generator",
                "input_scope": {"artifact_type": "flashcards", "scope": "recent artefact request"},
                "expected_output_schema": "ArtefactGenerationResult",
            }
        ],
    }
    backend = FakePlannerBackend([json.dumps(candidate), json.dumps(candidate)])

    plan = plan_workflow(
        backend,
        user_input="Wo sind die Flashcards?",
        selected_role="ScribeAgent",
        knowledge_mode="EXTERNALIZATION",
        distance="SWP",
        routing_reason="The user asks about generated flashcards.",
        retrieved_chunks=[],
        chat_history=[
            {
                "user": "All those concepts, find them in the sources and give me flashcards for all",
                "assistant": "Hier sind die Flashcards.",
            }
        ],
        parent_artefact_count=0,
        parent_message="Hier sind die Flashcards zu den Konzepten.",
    )

    assert plan.should_decompose is True
    assert plan.tasks[0].agent_role == "scribe_artifact_generator"
    assert plan.tasks[0].input_scope["artifact_type"] == "flashcards"
    prompt = backend.calls[0][0]
    assert "recent_chat_history" in prompt
    assert "parent_response" in prompt
    assert "artefact_count" in prompt
