# System Flow

Related docs:

- [IKMAS Overview](./IKMAS.md)
- [Architecture](./architecture.md)
- [Orchestrator](./orchestrator.md)
- [Router Agent](./router_agent.md)

```
User Input
↓
Intent
↓
Router Agent
↓
Route Decision
↓
Retrieval + Confidence
↓
Workflow Planning (NEW)
↓
Prompt Construction
↓
LLM (JSON only)
↓
Validation
↓
SQLite Log
↓
UI
```

The UI also exposes router telemetry via `router_debug` and workflow planning debug info via `workflow_planning_debug`.

When a workflow is planned:
```
User Input
↓
Intent
↓
Router Agent
↓
Route Decision
↓
Retrieval + Confidence
↓
Workflow Planning (NEW)
   ↓
Workflow Controller
   ↓
Worker Agents
   ↓
Aggregation
↓
Prompt Construction
↓
LLM (JSON only)
↓
Validation
↓
SQLite Log
↓
UI
```