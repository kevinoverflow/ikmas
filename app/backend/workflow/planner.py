from __future__ import annotations

import json
from json import JSONDecodeError
from typing import Any

from pydantic import BaseModel, Field

from app.backend.workflow.task_models import TaskPlan


ALLOWED_WORKFLOW_AGENTS: list[dict[str, str]] = [
    {
        "agent_role": "scribe_decision_extractor",
        "task_type": "extract_decisions",
        "use_when": "Extract explicit decisions and rationale from work traces, notes, transcripts, or documents.",
        "expected_output_schema": "DecisionExtractionResult",
    },
    {
        "agent_role": "scribe_assumption_extractor",
        "task_type": "extract_assumptions",
        "use_when": "Extract assumptions, constraints, dependencies, and applicability conditions.",
        "expected_output_schema": "AssumptionExtractionResult",
    },
    {
        "agent_role": "scribe_issue_extractor",
        "task_type": "extract_open_issues",
        "use_when": "Extract open questions, risks, unresolved issues, blockers, and action items.",
        "expected_output_schema": "OpenIssueExtractionResult",
    },
    {
        "agent_role": "scribe_concept_summary_writer",
        "task_type": "write_concept_learning_summaries",
        "use_when": "Create structured learning summaries for explicitly named concepts or topics.",
        "expected_output_schema": "ConceptLearningSummaryResult",
    },
    {
        "agent_role": "scribe_artifact_generator",
        "task_type": "generate_artefact",
        "use_when": "Generate a persisted artefact selected by input_scope.artifact_type. Supported artefact types: summary, flashcards, quiz, checklist, note, concept_map.",
        "expected_output_schema": "ArtefactGenerationResult",
    },
]


class PlanningAgentStep(BaseModel):
    agent_role: str
    status: str
    output: dict[str, Any] | None = None
    raw_output: str | None = None
    error: str | None = None


class WorkflowPlanningDecision(BaseModel):
    task_plan: TaskPlan
    debug: dict[str, Any] = Field(default_factory=dict)


def build_task_planner_prompt(
    *,
    user_input: str,
    selected_role: str,
    knowledge_mode: str,
    distance: str,
    routing_reason: str,
    retrieved_chunks: list[dict[str, Any]],
    chat_history: list[dict[str, str]] | None = None,
    parent_artefact_count: int = 0,
    parent_message: str = "",
) -> str:
    context_preview = []
    for chunk in retrieved_chunks[:3]:
        text = str(chunk.get("text", ""))[:800]
        context_preview.append(
            {
                "chunk_id": chunk.get("chunk_id"),
                "source": chunk.get("source"),
                "text_preview": text,
            }
        )

    return json.dumps(
        {
            "instruction": (
                "Decide whether this user turn should use a controlled multi-agent workflow. "
                "Return only a JSON TaskPlan. Do not answer the user request. "
                "Use decomposition only when separate bounded subtasks improve quality, coverage, "
                "or observability. Do not decompose simple requests."
            ),
            "selected_parent_role": selected_role,
            "routing_context": {
                "knowledge_mode": knowledge_mode,
                "distance": distance,
                "reason": routing_reason,
            },
            "recent_chat_history": (chat_history or [])[-5:],
            "parent_response": {
                "assistant_message": parent_message,
                "artefact_count": parent_artefact_count,
            },
            "allowed_worker_agents": ALLOWED_WORKFLOW_AGENTS,
            "required_output_schema": {
                "should_decompose": "boolean",
                "rationale": "string",
                "tasks": [
                    {
                        "task_id": "t1",
                        "task_type": "one allowed task_type",
                        "agent_role": "one allowed agent_role",
                        "input_scope": "object describing bounded scope",
                        "expected_output_schema": "matching schema name",
                        "dependencies": [],
                        "priority": 0,
                    }
                ],
                "aggregation_strategy": "scribe_knowledge_artifact or null",
            },
            "rules": [
                "Only use worker agents listed in allowed_worker_agents.",
                "If selected_parent_role is not ScribeAgent, set should_decompose=false unless an allowed worker clearly fits.",
                "If should_decompose=false, tasks must be [] and aggregation_strategy must be null.",
                "If should_decompose=true, include 1-5 tasks and set aggregation_strategy to scribe_knowledge_artifact.",
                "Use multi-agent workflow when the request asks for several deliverables, several concepts/topics, separate extraction dimensions, verification, synthesis, or a transparent trace.",
                "Use multi-agent workflow when the request asks to generate flashcards, quizzes, checklists, notes, concept maps, summaries, learning summaries, or other persisted study/work artefacts.",
                "If the current user asks where a prior artefact is, and recent chat history shows an unfulfilled request to create any artefact, plan the artefact generation now.",
                "If the parent response claims an artefact is done but parent_response.artefact_count is 0, plan a workflow task that creates the missing artefact.",
                "For generated artefacts, use agent_role=scribe_artifact_generator, task_type=generate_artefact, expected_output_schema=ArtefactGenerationResult, and set input_scope.artifact_type to one of: summary, flashcards, quiz, checklist, note, concept_map.",
                "A plan with one specialized worker task is valid when the worker is materially better suited than the parent response path.",
                "Prefer one task per distinct knowledge-work dimension or artifact type, not one task per sentence.",
            ],
            "examples": [
                {
                    "user_request_type": "learning summaries for multiple listed concepts",
                    "recommended_plan": {
                        "should_decompose": True,
                        "rationale": "The request asks for repeated structured artifacts across multiple concepts.",
                        "tasks": [
                            {
                                "task_id": "t1",
                                "task_type": "write_concept_learning_summaries",
                                "agent_role": "scribe_concept_summary_writer",
                                "input_scope": {"scope": "all explicitly listed concepts"},
                                "expected_output_schema": "ConceptLearningSummaryResult",
                                "dependencies": [],
                                "priority": 10,
                            }
                        ],
                        "aggregation_strategy": "scribe_knowledge_artifact",
                    },
                },
                {
                    "user_request_type": "persisted artefact such as flashcards, quiz, checklist, note, concept map, or summary",
                    "recommended_plan": {
                        "should_decompose": True,
                        "rationale": "The user requested a reusable artefact, so the workflow should create a persisted artefact object.",
                        "tasks": [
                            {
                                "task_id": "t1",
                                "task_type": "generate_artefact",
                                "agent_role": "scribe_artifact_generator",
                                "input_scope": {
                                    "artifact_type": "flashcards",
                                    "scope": "concepts from current request, recent chat history, and retrieved sources"
                                },
                                "expected_output_schema": "ArtefactGenerationResult",
                                "dependencies": [],
                                "priority": 10,
                            }
                        ],
                        "aggregation_strategy": "scribe_knowledge_artifact",
                    },
                },
                {
                    "user_request_type": "meeting notes containing decisions, assumptions, and open issues",
                    "recommended_plan": {
                        "should_decompose": True,
                        "rationale": "The input contains separate knowledge dimensions that should be extracted independently.",
                        "tasks": [
                            {
                                "task_id": "t1",
                                "task_type": "extract_decisions",
                                "agent_role": "scribe_decision_extractor",
                                "input_scope": {"scope": "decisions and rationale"},
                                "expected_output_schema": "DecisionExtractionResult",
                                "dependencies": [],
                                "priority": 10,
                            },
                            {
                                "task_id": "t2",
                                "task_type": "extract_assumptions",
                                "agent_role": "scribe_assumption_extractor",
                                "input_scope": {"scope": "assumptions and constraints"},
                                "expected_output_schema": "AssumptionExtractionResult",
                                "dependencies": [],
                                "priority": 5,
                            },
                            {
                                "task_id": "t3",
                                "task_type": "extract_open_issues",
                                "agent_role": "scribe_issue_extractor",
                                "input_scope": {"scope": "open issues, risks, and action items"},
                                "expected_output_schema": "OpenIssueExtractionResult",
                                "dependencies": [],
                                "priority": 5,
                            },
                        ],
                        "aggregation_strategy": "scribe_knowledge_artifact",
                    },
                },
            ],
            "user_input": user_input,
            "retrieved_context_preview": context_preview,
        },
        ensure_ascii=False,
        indent=2,
    )


def build_task_supervisor_prompt(
    *,
    user_input: str,
    selected_role: str,
    candidate_plan: TaskPlan,
    routing_reason: str,
) -> str:
    return json.dumps(
        {
            "instruction": (
                "Review the candidate TaskPlan from the workflow planner. "
                "Return the final TaskPlan JSON only. You may approve it, simplify it, "
                "or set should_decompose=false if multi-agent execution is not justified."
            ),
            "selected_parent_role": selected_role,
            "routing_reason": routing_reason,
            "allowed_worker_agents": ALLOWED_WORKFLOW_AGENTS,
            "candidate_task_plan": candidate_plan.model_dump(),
            "review_criteria": [
                "Does decomposition materially improve quality, coverage, or observability?",
                "Are all tasks bounded and non-overlapping?",
                "Are all worker roles allowed?",
                "Is the aggregation strategy valid?",
                "Would single-agent execution be clearer or cheaper for this request?",
                "Do not reject decomposition merely because there is only one specialized worker task.",
                "Preserve decomposition for requests with several concepts, several deliverables, or explicit structure requirements.",
            ],
            "user_input": user_input,
        },
        ensure_ascii=False,
        indent=2,
    )


def parse_task_plan(raw: str) -> TaskPlan:
    text = raw.strip()
    candidates = [text]
    if "```" in text:
        stripped = text.replace("```json", "```").replace("```JSON", "```")
        candidates.extend(part.strip() for part in stripped.split("```") if part.strip())
    first = text.find("{")
    last = text.rfind("}")
    if first != -1 and last != -1 and first < last:
        candidates.append(text[first:last + 1].strip())

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return TaskPlan.model_validate(parsed)

    raise JSONDecodeError("No TaskPlan JSON object found.", text, 0)


def fallback_single_agent_plan(reason: str = "Task planning failed or decomposition was not justified.") -> TaskPlan:
    return TaskPlan(
        should_decompose=False,
        rationale=reason,
        tasks=[],
        aggregation_strategy=None,
    )


def validate_planner_plan(plan: TaskPlan) -> tuple[TaskPlan, str]:
    allowed_roles = {agent["agent_role"] for agent in ALLOWED_WORKFLOW_AGENTS}
    allowed_pairs = {
        (agent["agent_role"], agent["task_type"], agent["expected_output_schema"])
        for agent in ALLOWED_WORKFLOW_AGENTS
    }
    if not plan.should_decompose:
        return (
            TaskPlan(
                should_decompose=False,
                rationale=plan.rationale,
                tasks=[],
                aggregation_strategy=None,
            ),
            "accepted_single_agent",
        )
    if not plan.tasks:
        return fallback_single_agent_plan("Planner requested decomposition but provided no tasks."), "rejected_no_tasks"
    if len(plan.tasks) > 5:
        return fallback_single_agent_plan("Planner requested too many tasks."), "rejected_too_many_tasks"
    for task in plan.tasks:
        if task.agent_role not in allowed_roles:
            return (
                fallback_single_agent_plan(f"Planner requested unknown worker role: {task.agent_role}."),
                f"rejected_unknown_worker:{task.agent_role}",
            )
        pair = (task.agent_role, task.task_type, task.expected_output_schema)
        if pair not in allowed_pairs:
            return (
                fallback_single_agent_plan(f"Planner requested an invalid task contract for {task.agent_role}."),
                f"rejected_invalid_contract:{task.agent_role}:{task.task_type}:{task.expected_output_schema}",
            )
    return (
        TaskPlan(
            should_decompose=True,
            rationale=plan.rationale,
            tasks=plan.tasks,
            aggregation_strategy=plan.aggregation_strategy or "scribe_knowledge_artifact",
        ),
        "accepted_multi_agent",
    )


def plan_workflow(
    backend: Any,
    *,
    user_input: str,
    selected_role: str,
    knowledge_mode: str,
    distance: str,
    routing_reason: str,
    retrieved_chunks: list[dict[str, Any]],
    chat_history: list[dict[str, str]] | None = None,
    parent_artefact_count: int = 0,
    parent_message: str = "",
) -> TaskPlan:
    return plan_workflow_decision(
        backend,
        user_input=user_input,
        selected_role=selected_role,
        knowledge_mode=knowledge_mode,
        distance=distance,
        routing_reason=routing_reason,
        retrieved_chunks=retrieved_chunks,
        chat_history=chat_history,
        parent_artefact_count=parent_artefact_count,
        parent_message=parent_message,
    ).task_plan


def plan_workflow_decision(
    backend: Any,
    *,
    user_input: str,
    selected_role: str,
    knowledge_mode: str,
    distance: str,
    routing_reason: str,
    retrieved_chunks: list[dict[str, Any]],
    chat_history: list[dict[str, str]] | None = None,
    parent_artefact_count: int = 0,
    parent_message: str = "",
) -> WorkflowPlanningDecision:
    prompt = build_task_planner_prompt(
        user_input=user_input,
        selected_role=selected_role,
        knowledge_mode=knowledge_mode,
        distance=distance,
        routing_reason=routing_reason,
        retrieved_chunks=retrieved_chunks,
        chat_history=chat_history,
        parent_artefact_count=parent_artefact_count,
        parent_message=parent_message,
    )
    steps: list[PlanningAgentStep] = []
    try:
        proposer_raw = backend.generate(
            prompt,
            system_prompt=(
                "You are IKMAS Workflow Planner Agent. Return only valid JSON matching TaskPlan. "
                "Never invent worker agents."
            ),
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        candidate_plan = parse_task_plan(proposer_raw)
        steps.append(
            PlanningAgentStep(
                agent_role="workflow_planner_agent",
                status="success",
                output=candidate_plan.model_dump(),
                raw_output=proposer_raw,
            )
        )
    except Exception as exc:
        fallback = fallback_single_agent_plan()
        steps.append(
            PlanningAgentStep(
                agent_role="workflow_planner_agent",
                status="failed",
                error=str(exc),
            )
        )
        return WorkflowPlanningDecision(
            task_plan=fallback,
            debug={
                "planning_mode": "multi_agent_planning",
                "selected_plan_source": "fallback",
                "validation_status": "planner_failed",
                "steps": [step.model_dump() for step in steps],
            },
        )

    supervisor_prompt = build_task_supervisor_prompt(
        user_input=user_input,
        selected_role=selected_role,
        candidate_plan=candidate_plan,
        routing_reason=routing_reason,
    )
    try:
        supervisor_raw = backend.generate(
            supervisor_prompt,
            system_prompt=(
                "You are IKMAS Workflow Supervisor Agent. Return only the final valid TaskPlan JSON. "
                "Reject unnecessary decomposition and never invent worker agents."
            ),
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        supervised_plan = parse_task_plan(supervisor_raw)
        steps.append(
            PlanningAgentStep(
                agent_role="workflow_supervisor_agent",
                status="success",
                output=supervised_plan.model_dump(),
                raw_output=supervisor_raw,
            )
        )
        final_plan, validation_status = validate_planner_plan(supervised_plan)
        selected_source = "workflow_supervisor_agent"
    except Exception as exc:
        final_plan, validation_status = validate_planner_plan(candidate_plan)
        steps.append(
            PlanningAgentStep(
                agent_role="workflow_supervisor_agent",
                status="failed",
                error=str(exc),
            )
        )
        selected_source = "workflow_planner_agent"

    return WorkflowPlanningDecision(
        task_plan=final_plan,
        debug={
            "planning_mode": "multi_agent_planning",
            "selected_plan_source": selected_source,
            "validation_status": validation_status,
            "steps": [step.model_dump() for step in steps],
        },
    )
