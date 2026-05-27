# Agentic Workflow Architecture

This document describes the agentic workflow architecture implemented in IKMAS.

## Overview

IKMAS now supports controlled agentic workflows where parent agents can propose structured task plans that are validated and executed by a deterministic workflow controller. This preserves the benefits of agentic decomposition while maintaining safety, observability, and testability.

## Core Components

### 1. Task Models
- `TaskPlan`: Structured output of parent agents when decomposition is useful
- `TaskSpec`: Describes a single bounded unit of work
- `AgentTaskResult`: Typed results from executing tasks
- `AgentTrace`: Execution traces for transparency
- `ExecutionBudget`: Bounded limits for workflow execution
- `WorkflowResult`: Final aggregated results

### 2. Agent Registry
A static registry of approved agent templates that prevents arbitrary agent creation.

### 3. Workflow Controller
The central runtime component that:
- Validates TaskPlans
- Enforces ExecutionBudget limits
- Executes approved worker tasks
- Collects results and builds traces
- Calls aggregators

### 4. Worker Agents
Specialized agents that execute specific subtasks:
- `ScribeDecisionExtractor`
- `ScribeAssumptionExtractor` 
- `ScribeIssueExtractor`
- `ScribeConceptSummaryWriter`
- `ScribeArtifactGenerator`

### 5. Aggregators
Components that combine task results into final structured artifacts:
- `ScribeAggregator` for reusable knowledge artifacts

## Architecture Diagram

```text
User Input
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
   ├── execute tasks
   └── collect results
   ↓
Aggregator
   ↓
Validator
   ↓
AssistantPayload + AgentTrace
   ↓
UI
```

## Implementation Details

### Workflow Execution Flow
1. Parent agent proposes a `TaskPlan` with decomposition rationale
2. `WorkflowController` validates the plan against registry and budget
3. Tasks are executed sequentially using registered agents
4. Results are collected as `AgentTaskResult` objects
5. Aggregator combines results into final artifact
6. Trace is built and returned with the response

### Safety Measures
- No recursive `handle_turn` calls for subagents
- Static agent registry prevents arbitrary agent creation
- Execution budgets bound computational resources
- Typed contracts prevent generic data structures

### New Worker Agents Added
- `ScribeConceptSummaryWriter`: Creates structured learning summaries for explicitly named concepts
- `ScribeArtifactGenerator`: Generates persisted study/work artefacts (flashcards, quizzes, checklists, etc.)

This implementation represents Phase 1 of the phased approach outlined in `truly_agentic_ikmas_revised.md`.