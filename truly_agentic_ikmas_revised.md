# Making IKMAS Truly Agentic: Revised Architecture and Implementation Plan

## 1. Executive Summary

This document defines a revised architecture for transforming IKMAS from a static, role-routed assistant into a controlled agentic knowledge-work system.

The goal is **not** to let LLM agents freely spawn arbitrary agents. Instead, IKMAS should allow parent agents to propose structured task plans, which are then validated and executed by a deterministic workflow controller. This preserves the benefits of agentic decomposition while keeping the system safe, observable, testable, and suitable for academic evaluation.

The core architectural shift is:

```text
Current model:
User input → Router → One selected agent → One response

Revised agentic model:
User input → Router → Parent agent → TaskPlan → WorkflowController → Specialized task agents → Aggregator → Validated response + trace
```

This design supports workflows such as:

- Scribe Agent decomposing meeting notes into decisions, assumptions, rationale, unresolved issues, stakeholders, and reuse guidance.
- Mentor Agent generating explanations, examples, quizzes, and misconception checks as coordinated subtasks.
- Research Agent separating literature mapping, claim checking, method critique, and gap analysis.

The system becomes agentic because it can dynamically decompose complex knowledge tasks, delegate subtasks to specialized agents, monitor execution, aggregate results, and expose a transparent execution trace.

---

## 2. Design Principle

IKMAS should not implement uncontrolled agent spawning.

Instead:

> Agents propose structured task plans. The system validates, schedules, executes, aggregates, and traces those plans.

This distinction is central.

Bad design:

```text
Agent decides to spawn arbitrary subagents → Orchestrator recursively calls handle_turn → Results are concatenated
```

Better design:

```text
Agent proposes TaskPlan → WorkflowController validates plan → Approved task agents execute bounded subtasks → Aggregator synthesizes result → Validator checks quality and schema
```

This keeps autonomy at the planning level while preserving deterministic control at the execution level.

---

## 3. Current Architecture Limitation

The current IKMAS architecture is based on a static role-routing pattern:

1. User input is received.
2. Router selects a role or agent.
3. FSM determines the high-level execution state.
4. Orchestrator runs retrieval, generation, validation, and fallback logic.
5. A single assistant payload is returned.

This works well for simple or moderately complex requests, but it has limitations:

- Only one main agent is executed per user turn.
- Complex tasks are handled monolithically.
- There is no structured task decomposition layer.
- There is no controlled subtask execution model.
- There is no explicit parent-child agent trace.
- Aggregation is not modeled as a first-class concern.
- Evaluation data for multi-step knowledge workflows is limited.

For IKMAS, these limitations matter because knowledge-intensive work often requires decomposition, comparison, critique, synthesis, and reuse-aware structuring.

---

## 4. Target Architecture

### 4.1 High-Level Flow

```text
User Input
   ↓
handle_turn
   ↓
Router Agent
   ↓
Parent Agent
   ↓
TaskPlan generation
   ↓
WorkflowController
   ├── validate plan
   ├── enforce budget
   ├── resolve dependencies
   ├── schedule tasks
   ├── execute specialized agents
   └── collect task results
   ↓
Aggregator
   ↓
Validator
   ↓
AssistantPayload + AgentTrace
   ↓
UI
```

### 4.2 Important Boundary

`handle_turn` should remain the public entry point for one user interaction.

Subagents should **not** call `handle_turn` recursively. Recursive `handle_turn` calls make subagent execution look like new user turns, which can pollute chat history, trigger unnecessary routing, distort telemetry, and make debugging difficult.

Instead, subagents should be executed through a lower-level internal interface:

```python
def execute_agent_task(
    agent_id: str,
    task: TaskSpec,
    context: ExecutionContext,
) -> AgentTaskResult:
    ...
```

---

## 5. Core Concepts

## 5.1 TaskPlan

A `TaskPlan` is the structured output of a parent agent when decomposition is useful.

```python
from pydantic import BaseModel, Field
from typing import Literal

class TaskPlan(BaseModel):
    should_decompose: bool
    rationale: str
    tasks: list["TaskSpec"] = Field(default_factory=list)
    aggregation_strategy: str | None = None
```

The parent agent does not directly spawn agents. It explains whether decomposition is useful and proposes bounded subtasks.

Example:

```json
{
  "should_decompose": true,
  "rationale": "The input contains multiple independent sections with different knowledge reuse requirements.",
  "tasks": [
    {
      "task_id": "t1",
      "task_type": "extract_decisions",
      "agent_role": "scribe_decision_extractor",
      "input_scope": {"section": "Planning decisions"},
      "expected_output_schema": "DecisionExtractionResult",
      "dependencies": []
    },
    {
      "task_id": "t2",
      "task_type": "extract_open_issues",
      "agent_role": "scribe_issue_extractor",
      "input_scope": {"section": "Risks and open questions"},
      "expected_output_schema": "OpenIssueExtractionResult",
      "dependencies": []
    }
  ],
  "aggregation_strategy": "scribe_knowledge_artifact"
}
```

---

## 5.2 TaskSpec

A `TaskSpec` describes a single bounded unit of work.

```python
class TaskSpec(BaseModel):
    task_id: str
    task_type: str
    agent_role: str
    input_scope: dict
    expected_output_schema: str
    dependencies: list[str] = Field(default_factory=list)
    priority: int = 0
    max_tokens: int | None = None
    timeout_seconds: int | None = None
```

A task is not an agent. A task is a unit of work. The system maps tasks to allowed agent templates.

---

## 5.3 AgentTaskResult

Every subtask returns a typed result.

```python
class AgentTaskResult(BaseModel):
    task_id: str
    agent_role: str
    status: Literal["success", "failed", "skipped"]
    output: dict | None = None
    error: str | None = None
    citations: list[dict] = Field(default_factory=list)
    artefacts: list[dict] = Field(default_factory=list)
    telemetry: dict = Field(default_factory=dict)
```

This allows aggregation to distinguish successful, failed, and skipped work.

---

## 5.4 AgentTrace

Agentic execution must be transparent.

```python
class AgentTraceNode(BaseModel):
    task_id: str
    agent_role: str
    parent_agent: str | None = None
    status: Literal["planned", "running", "success", "failed", "skipped"]
    started_at: float | None = None
    finished_at: float | None = None
    dependencies: list[str] = Field(default_factory=list)
    error: str | None = None

class AgentTrace(BaseModel):
    root_agent: str
    nodes: list[AgentTraceNode] = Field(default_factory=list)
    total_tasks: int = 0
    successful_tasks: int = 0
    failed_tasks: int = 0
    max_depth_observed: int = 0
```

The UI should expose this trace in a simple tree or timeline.

---

## 5.5 ExecutionBudget

Agentic workflows must be bounded.

```python
class ExecutionBudget(BaseModel):
    max_subagents: int = 5
    max_depth: int = 2
    max_total_tokens: int = 12000
    max_wall_time_seconds: int = 60
    max_retrieval_calls: int = 8
    allow_parallel_execution: bool = False
```

The first implementation should keep execution synchronous and bounded. Parallel execution can be added later after the workflow contracts are stable.

---

## 6. Agent Registry

IKMAS should not dynamically create arbitrary new agent roles at runtime.

Instead, it should use a static registry of approved agent templates.

```python
AGENT_REGISTRY = {
    "scribe_decision_extractor": ScribeDecisionExtractor,
    "scribe_assumption_extractor": ScribeAssumptionExtractor,
    "scribe_issue_extractor": ScribeIssueExtractor,
    "scribe_reuse_context_writer": ScribeReuseContextWriter,
    "mentor_quiz_generator": MentorQuizGenerator,
    "mentor_misconception_checker": MentorMisconceptionChecker,
    "research_claim_checker": ResearchClaimChecker,
    "research_gap_finder": ResearchGapFinder,
}
```

This improves:

- safety,
- testability,
- prompt quality,
- output consistency,
- observability,
- evaluation reliability.

Dynamic registration can be considered later, but it should not be part of the initial implementation.

---

## 7. WorkflowController

The `WorkflowController` is the central runtime component for agentic execution.

Responsibilities:

1. Validate the `TaskPlan`.
2. Check agent roles against the registry.
3. Enforce budget limits.
4. Resolve task dependencies.
5. Schedule tasks.
6. Execute specialized agents.
7. Collect task results.
8. Handle failures and retries.
9. Build an execution trace.
10. Pass results to the correct aggregator.

Example interface:

```python
class WorkflowController:
    def __init__(self, registry: AgentRegistry, budget: ExecutionBudget):
        self.registry = registry
        self.budget = budget

    def run(
        self,
        plan: TaskPlan,
        context: "ExecutionContext",
    ) -> "WorkflowResult":
        self.validate_plan(plan)
        self.enforce_budget(plan)
        ordered_tasks = self.resolve_dependencies(plan.tasks)
        results = []

        for task in ordered_tasks:
            result = self.execute_task(task, context)
            results.append(result)

        return WorkflowResult(
            results=results,
            trace=self.build_trace(results),
            aggregation_strategy=plan.aggregation_strategy,
        )
```

---

## 8. Aggregation

Aggregation is a first-class part of the architecture.

The system should not simply concatenate subagent outputs. Each parent agent should define an aggregation strategy.

### 8.1 Scribe Aggregation

The Scribe Agent should aggregate into a reusable knowledge artifact.

```json
{
  "artifact_type": "reusable_knowledge_artifact",
  "decisions": [],
  "rationale": [],
  "assumptions": [],
  "stakeholders": [],
  "open_issues": [],
  "reuse_guidance": [],
  "confidence_notes": [],
  "source_map": []
}
```

### 8.2 Mentor Aggregation

The Mentor Agent should aggregate into a learning package.

```json
{
  "artifact_type": "learning_package",
  "concept_summary": "",
  "examples": [],
  "quiz_questions": [],
  "misconceptions": [],
  "next_steps": []
}
```

### 8.3 Research Aggregation

The Research Agent should aggregate into a research support artifact.

```json
{
  "artifact_type": "research_analysis",
  "claims": [],
  "supporting_evidence": [],
  "contradictions": [],
  "methodological_notes": [],
  "research_gaps": [],
  "confidence_notes": []
}
```

---

## 9. Spawning Policy

Subagents should only be used when they improve quality, structure, or reliability.

### 9.1 Spawn When

A parent agent may propose decomposition when one or more conditions are true:

- The input contains at least three clearly separable sections.
- The requested output requires multiple artifact types.
- The task benefits from independent critique or verification.
- The task requires extraction of different knowledge dimensions.
- The user explicitly asks for deep, structured, or multi-perspective analysis.
- The input is too complex for a single coherent pass.

### 9.2 Do Not Spawn When

The system should avoid decomposition when:

- The request is simple.
- The input is short.
- Subtask outputs would be redundant.
- The task needs a single coherent voice.
- The latency or token budget is low.
- The parent agent can reliably complete the task alone.

### 9.3 Default Initial Limits

```python
DEFAULT_AGENTIC_BUDGET = ExecutionBudget(
    max_subagents=5,
    max_depth=2,
    max_total_tokens=12000,
    max_wall_time_seconds=60,
    max_retrieval_calls=8,
    allow_parallel_execution=False,
)
```

---

## 10. Failure Handling

Agentic workflows must degrade gracefully.

Recommended behavior:

1. If task planning fails, fall back to normal single-agent execution.
2. If a task result fails schema validation, retry once with a repair prompt.
3. If the retry fails, mark the task as failed and continue aggregation with partial results.
4. If too many tasks fail, return a partial artifact with explicit failure notes.
5. If budget is exceeded, stop scheduling new tasks and aggregate completed results.

Example failure note:

```json
{
  "status": "partial_success",
  "failed_tasks": ["t3"],
  "message": "The artifact was generated with partial results. Open issue extraction failed after one retry."
}
```

---

## 11. Schema Changes

### 11.1 Extend AssistantPayload

The existing `AssistantPayload` should be extended carefully. Avoid generic `list[dict]` fields where possible.

Recommended additions:

```python
class AssistantPayload(BaseModel):
    # existing fields remain unchanged
    task_plan: TaskPlan | None = None
    agent_trace: AgentTrace | None = None
    workflow_result: dict | None = None
```

Do not add vague fields such as:

```python
agent_spawning_instructions: list[dict]
subagent_results: list[dict]
```

Typed models will make validation, testing, UI rendering, and research evaluation much easier.

### 11.2 Add Workflow Models

Add a new file:

```text
app/domain/workflow.py
```

Suggested models:

- `TaskPlan`
- `TaskSpec`
- `AgentTaskResult`
- `AgentTraceNode`
- `AgentTrace`
- `ExecutionBudget`
- `WorkflowResult`

---

## 12. FSM Integration

The FSM should not be overloaded with internal runtime states such as:

- `AGENT_SPAWNING`
- `SUBAGENT_EXECUTION`
- `SUBAGENT_COLLECTION`
- `RESULT_AGGREGATION`

These are workflow lifecycle phases, not high-level conversation states.

Recommended approach:

```text
FSM decides high-level mode.
WorkflowController handles internal agentic execution.
```

Possible high-level FSM addition:

```python
if session_ctx.get("agentic_mode", False):
    return "AGENTIC_WORKFLOW"
```

But even this may not be necessary if the orchestrator can invoke the workflow controller inside the existing generation path.

---

## 13. Orchestrator Integration

The orchestrator should remain responsible for one user turn.

Recommended structure:

```python
def handle_turn(...):
    route = route_with_agent(...)
    state = decide_state(...)

    parent_output = run_parent_agent(...)

    if parent_output.task_plan and parent_output.task_plan.should_decompose:
        workflow_result = workflow_controller.run(
            plan=parent_output.task_plan,
            context=execution_context,
        )
        aggregated = aggregate_workflow_result(
            strategy=workflow_result.aggregation_strategy,
            results=workflow_result.results,
            context=execution_context,
        )
        validated = validate_aggregated_output(aggregated)
        return build_assistant_payload(validated, workflow_result.trace)

    return build_assistant_payload(parent_output)
```

Important: subagents should use `execute_agent_task`, not `handle_turn`.

---

## 14. Prompting Changes

Parent agents should be prompted to decide whether decomposition is useful and to emit a `TaskPlan` only when justified.

### 14.1 Parent Agent Prompt Pattern

```text
You may propose a structured task plan when the user request is complex enough to benefit from decomposition.

Do not create arbitrary agents.
Do not decompose simple requests.
Only use allowed task types and agent roles.
For each task, specify:
- task_id
- task_type
- agent_role
- input_scope
- expected_output_schema
- dependencies

If decomposition is not useful, set should_decompose=false and answer normally.
```

### 14.2 Scribe Agent Decomposition Prompt

```text
As Scribe Agent, decompose only when the input contains multiple knowledge dimensions or sections.
Useful decomposition dimensions include:
- decisions
- rationale
- assumptions
- stakeholders
- unresolved issues
- reuse guidance

Your final goal is not merely summarization. Your goal is to create explicit, reusable knowledge artifacts.
```

---

## 15. UI Requirements

The UI should make agentic execution visible but not overwhelming.

Minimum UI additions:

1. Show whether agentic workflow was used.
2. Show parent agent.
3. Show task tree or task list.
4. Show task statuses.
5. Show partial failures.
6. Show final aggregation result.

Example:

```text
Agentic workflow used: Yes
Parent agent: Scribe Agent

Tasks:
✓ Decision Extractor
✓ Assumption Extractor
✓ Open Issue Extractor
✓ Reuse Context Writer

Final artifact: Reusable Knowledge Artifact
```

Advanced UI additions:

- expandable trace tree,
- per-agent output preview,
- token/runtime telemetry,
- source-to-claim map,
- failure diagnostics.

---

## 16. Persistence Requirements

Store agentic workflow metadata in session history.

Persist:

- task plan,
- task results,
- agent trace,
- aggregation strategy,
- final artifact,
- telemetry,
- failure notes.

This supports:

- debugging,
- user transparency,
- later reuse,
- academic evaluation,
- comparison of single-agent vs agentic workflows.

---

## 17. Telemetry and Evaluation

Agentic IKMAS should collect telemetry suitable for both engineering and research evaluation.

### 17.1 Engineering Telemetry

Track:

- number of tasks,
- successful tasks,
- failed tasks,
- retries,
- runtime,
- token usage,
- retrieval calls,
- max depth,
- aggregation strategy.

### 17.2 Research Evaluation

Agentic workflows should be evaluated against the non-agentic baseline.

Potential evaluation dimensions:

| Dimension | Possible Metric |
|---|---|
| Artifact quality | expert rating |
| Knowledge reuse support | presence of decisions, rationale, assumptions, unresolved issues, reuse context |
| Traceability | source-to-claim mapping quality |
| Transparency | user-rated understandability of workflow |
| Robustness | success under complex or messy inputs |
| Efficiency | time-to-artifact |
| Cost | tokens and runtime |

A strong research claim would be:

> Controlled agentic decomposition improves the structure, traceability, and reuse-readiness of generated knowledge artifacts compared to single-agent generation.

Avoid unsupported claims such as:

> The system is self-optimizing.

Unless actual feedback loops and policy learning are implemented.

---

## 18. Implementation Phases

## Phase 1: Typed Workflow Foundation

Create:

```text
app/domain/workflow.py
```

Implement:

- `TaskPlan`
- `TaskSpec`
- `AgentTaskResult`
- `AgentTrace`
- `ExecutionBudget`
- `WorkflowResult`

Update:

- schema tests,
- validation logic,
- payload serialization.

Do not implement recursive subagent execution in this phase.

---

## Phase 2: Agent Registry and Task Executor

Create:

```text
app/backend/agent_registry.py
app/backend/agent_task_executor.py
```

Implement:

- static registry of approved task agents,
- `execute_agent_task`,
- task-level prompt execution,
- schema validation per task,
- basic telemetry.

Initial supported Scribe agents:

- `scribe_decision_extractor`
- `scribe_assumption_extractor`
- `scribe_issue_extractor`
- `scribe_reuse_context_writer`

---

## Phase 3: WorkflowController

Create:

```text
app/backend/workflow_controller.py
```

Implement:

- plan validation,
- budget enforcement,
- dependency resolution,
- sequential execution,
- retry once on validation failure,
- trace construction,
- partial failure handling.

Parallel execution should not be implemented yet.

---

## Phase 4: Scribe Agentic Workflow

Start with one controlled use case: Scribe Agent for reusable knowledge artifacts.

Implement:

- Scribe parent prompt with `TaskPlan` output,
- Scribe-specific task agents,
- Scribe aggregation strategy,
- validation of final reusable knowledge artifact.

This phase should produce a working end-to-end agentic workflow.

---

## Phase 5: UI Trace and Persistence

Update the UI to display:

- whether agentic workflow was used,
- task list,
- task statuses,
- partial failures,
- final artifact,
- trace details.

Persist:

- `TaskPlan`,
- `AgentTaskResult`,
- `AgentTrace`,
- final aggregated artifact.

---

## Phase 6: Extend to Mentor and Research Agents

After the Scribe workflow is stable, add controlled workflows for:

### Mentor Agent

Possible task agents:

- concept explainer,
- example generator,
- quiz generator,
- misconception checker.

### Research Agent

Possible task agents:

- claim checker,
- literature mapper,
- method critic,
- research gap finder.

---

## Phase 7: Optional Parallel Execution

Only after correctness and traceability are stable, add async or parallel execution.

Requirements before parallel execution:

- stable task contracts,
- deterministic aggregation,
- timeout handling,
- robust error handling,
- telemetry per task,
- concurrency-safe session handling.

---

## 19. Testing Strategy

### 19.1 Unit Tests

Test:

- workflow schema validation,
- task plan validation,
- registry lookup,
- budget enforcement,
- dependency resolution,
- aggregation logic.

### 19.2 Integration Tests

Test:

- Scribe Agent creates valid `TaskPlan`,
- WorkflowController executes all tasks,
- failed task is retried once,
- partial failure still produces usable output,
- final artifact matches schema,
- trace is persisted.

### 19.3 Regression Tests

Ensure:

- simple requests still use normal single-agent execution,
- existing payloads remain compatible,
- existing router and FSM behavior is not broken,
- non-agentic flows remain fast.

### 19.4 Evaluation Tests

Compare:

- single-agent Scribe output,
- agentic Scribe output,
- artifact completeness,
- traceability,
- knowledge reuse readiness,
- user-rated usefulness.

---

## 20. What This Architecture Is Not

This architecture is not:

- uncontrolled recursive agent spawning,
- arbitrary runtime creation of new agent roles,
- self-modifying code,
- self-optimization,
- a fully autonomous agent society,
- a replacement for the existing router/orchestrator/FSM architecture.

It is:

- controlled task decomposition,
- typed subtask execution,
- validated aggregation,
- traceable multi-agent knowledge work,
- an incremental extension of the current IKMAS architecture.

---

## 21. Recommended Research Framing

A strong thesis framing:

> IKMAS evolves from a static role-routed assistant into a controlled agentic knowledge-work system. Complex knowledge tasks are decomposed into typed subtasks, delegated to specialized role agents, validated against explicit output contracts, and aggregated into reusable knowledge artifacts with transparent provenance.

Potential research contribution:

> The contribution is not merely the use of multiple agents, but the design of a controlled agentic workflow architecture for knowledge reuse, combining task decomposition, role-specialized generation, traceable aggregation, and evaluation of reuse-readiness.

---

## 22. Minimal Viable Agentic Version

The first working version should be intentionally narrow.

Minimum viable implementation:

1. Scribe Agent can produce a `TaskPlan`.
2. WorkflowController validates the plan.
3. Four approved Scribe task agents execute sequentially.
4. Aggregator creates a reusable knowledge artifact.
5. Validator checks the artifact schema.
6. UI displays task trace.
7. Telemetry is stored.

This is enough to demonstrate true controlled agentic behavior without overengineering the system.

---

## 23. Final Recommendation

Implement agentic IKMAS as a controlled workflow layer, not as recursive agent spawning.

Prioritize:

1. Typed task contracts.
2. Static approved agent registry.
3. WorkflowController.
4. Scribe-first implementation.
5. Aggregation strategies.
6. Trace UI.
7. Evaluation against non-agentic baseline.

Avoid:

1. Recursive `handle_turn` calls for subagents.
2. Generic `list[dict]` payload fields.
3. Arbitrary dynamic agent creation.
4. Claims of self-optimization without feedback learning.
5. Adding too many FSM states for internal workflow phases.

This design is safer, more testable, more research-defensible, and better aligned with IKMAS as an Intelligent Knowledge Management Assistance System.
