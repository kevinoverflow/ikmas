# IKMAS v2 Implementation Plan

## Purpose

IKMAS v2 rebuilds the current implementation-first Streamlit/RAG prototype into an API-first, agent-based knowledge management framework. The legacy implementation remains a reference prototype, while v2 introduces a clean backend architecture, reusable agent runtime, workflow engine, MCP-compatible integration layer, React client, and evaluation framework.

## Target Vision

IKMAS v2 is an agent-based framework for knowledge-intensive work. It supports knowledge ingestion, retrieval, transformation, reuse, evaluation, and traceability through configurable agents and workflows.

The system should be usable through multiple clients:

- React web application
- Future SwiftUI client
- CLI and evaluation scripts
- External AI clients through an IKMAS MCP server

## Architectural Direction

IKMAS v2 is backend-first.

```text
React / SwiftUI / CLI / External AI Clients
        -> IKMAS API
        -> IKMAS Agent Runtime
        -> Workflow Engine
        -> Knowledge Infrastructure
        -> Native Tools + MCP Tools
```

The UI must not own business logic, prompt logic, retrieval behavior, memory, evaluation, or workflow orchestration.

## Core Principles

1. API-first, not UI-first.
2. Agent framework, not fixed chatbot.
3. Workflows are explicit, typed, observable, and evaluatable.
4. MCP is an integration layer, not the whole framework.
5. Knowledge objects are first-class entities.
6. Every meaningful output should be traceable to inputs, sources, tool calls, and agent runs.
7. Evaluation is part of the system, not an afterthought.
8. Legacy code is a reference, not the foundation.

## Implementation Phases

### Phase 0: Legacy Freeze and Planning

Goals:

- Freeze the current prototype.
- Document what exists, what works, and what should not be reused.
- Establish v2 architecture and migration boundaries.

Deliverables:

- `docs/v2/implementation-plan.md`
- `docs/v2/architecture.md`
- `docs/v2/migration-strategy.md`
- `docs/v2/legacy-audit.md`

Exit criteria:

- Current implementation is documented as legacy.
- v2 scope and architecture are clear.

### Phase 1: Backend Foundation

Goals:

- Create a clean FastAPI backend.
- Establish project structure, configuration, logging, errors, tests, and domain models.

Deliverables:

- `backend/pyproject.toml`
- `backend/src/ikmas/main.py`
- `backend/src/ikmas/core/`
- `backend/src/ikmas/domain/`
- `backend/tests/`

Initial modules:

```text
backend/src/ikmas/
├─ api/
├─ core/
├─ domain/
├─ framework/
├─ knowledge/
├─ integrations/
├─ applications/
└─ evaluation/
```

Exit criteria:

- `GET /health` works.
- Backend has a testable structure.
- Core domain models are defined.

### Phase 2: Agent Runtime MVP

Goals:

- Implement the generic agent runtime.
- Support typed agent definitions, tool calls, structured outputs, and run traces.

Deliverables:

- Agent model
- Tool interface
- Agent executor
- Prompt rendering
- Structured output parser
- Trace events

Required abstractions:

- `AgentSpec`
- `ToolSpec`
- `AgentRun`
- `ToolCall`
- `TraceEvent`
- `Policy`

Exit criteria:

- A simple agent can run through the API.
- Tool calls are captured in a trace.
- Agent input and output are schema-controlled.

### Phase 3: Knowledge Infrastructure MVP

Goals:

- Implement documents, chunks, retrieval, and knowledge objects.
- Provide source-grounded answers.

Deliverables:

- Document upload endpoint
- Text extraction pipeline
- Chunking pipeline
- Vector store adapter
- Retrieval tool
- Knowledge object store

Exit criteria:

- User can upload a document.
- Document can be indexed.
- Retrieval returns chunks with metadata.
- Agent can answer with sources.

### Phase 4: Workflow Engine MVP

Goals:

- Implement explicit workflows composed of agents and tools.
- Support sequential workflows first; graph routing later.

Deliverables:

- Workflow definition model
- Workflow executor
- Run state model
- Trace viewer API
- First SECI-inspired workflow

Initial workflow:

```text
Retrieve relevant material
 -> Externalize knowledge objects
 -> Critique grounding/usefulness
 -> Store accepted knowledge objects
```

Exit criteria:

- A workflow can be started through the API.
- Each step is traceable.
- Workflow outputs are persisted.

### Phase 5: MCP Integration Layer

Goals:

- Allow IKMAS agents to consume external MCP tools.
- Later expose IKMAS capabilities as an MCP server.

Deliverables:

- MCP client adapter
- MCP tool registry bridge
- MCP permission policy
- MCP server prototype for selected IKMAS tools

Initial MCP tools exposed by IKMAS:

- `search_knowledge_base`
- `create_knowledge_object`
- `run_workflow`
- `get_trace`
- `recommend_knowledge_reuse`

Exit criteria:

- MCP tools can be registered as IKMAS tools.
- Tool calls are permissioned and traced.
- Destructive tools require confirmation or are disabled by default.

### Phase 6: React Client MVP

Goals:

- Build a web UI around agent workspaces, not a chatbot-only interface.

Deliverables:

- React/Vite frontend
- API client
- Workspace view
- Document upload
- Agent/task runner
- Workflow runner
- Run trace view
- Source viewer

Exit criteria:

- User can upload documents, run a workflow, inspect outputs, and view traces.

### Phase 7: Evaluation Framework

Goals:

- Make IKMAS research-ready.
- Evaluate retrieval, groundedness, usefulness, traceability, and knowledge reuse quality.

Deliverables:

- Evaluation datasets
- Metrics
- Rubrics
- Experiment runner
- Exportable results

Exit criteria:

- A workflow can be evaluated repeatedly on a fixed dataset.
- Results can support thesis/paper claims.

### Phase 8: Advanced Framework Capabilities

Goals:

- Extend beyond MVP once the foundation is stable.

Possible additions:

- Conditional workflow graphs
- Human-in-the-loop approval checkpoints
- Multi-agent debate/review patterns
- Workspace memory
- User-level permissions
- SwiftUI client
- External plugin ecosystem

## First Vertical Slice

The first working v2 slice should be:

```text
Upload prototype notes
 -> Ingest and index document
 -> Run Externalization Workflow
 -> Retrieval Agent finds relevant material
 -> Externalization Agent extracts knowledge objects
 -> Critic Agent evaluates grounding/usefulness
 -> Accepted knowledge objects are stored
 -> React UI shows result, sources, and trace
```

This slice demonstrates:

- Agent framework
- Knowledge management
- SECI externalization
- Retrieval grounding
- Traceability
- Evaluation potential
- API-first architecture

## Initial Commit Roadmap

1. Add v2 planning docs.
2. Initialize backend structure.
3. Add core config, logging, and health endpoint.
4. Add domain models.
5. Add agent and tool interfaces.
6. Add trace model and trace store.
7. Add document and knowledge object models.
8. Add ingestion pipeline.
9. Add retrieval tool.
10. Add minimal agent executor.
11. Add workflow executor.
12. Add first externalization workflow.
13. Add React frontend shell.
14. Add document upload and workflow run UI.
15. Add trace viewer.
16. Add evaluation runner.

## Non-Goals for MVP

- Fully autonomous agents.
- Complex multi-agent self-planning.
- Production-grade permission system.
- Native SwiftUI client.
- Plugin marketplace.
- Premature microservices.
- UI-specific business logic.

## Success Criteria

IKMAS v2 is successful when:

- The backend can run agent workflows independently from the UI.
- Agents, tools, workflows, runs, traces, and knowledge objects are explicit entities.
- React is only a client, not the system core.
- MCP can extend the tool layer without controlling the framework architecture.
- System behavior can be evaluated and reproduced.
- The architecture supports the research positioning of IKMAS as an agent-based framework for knowledge-intensive work.
