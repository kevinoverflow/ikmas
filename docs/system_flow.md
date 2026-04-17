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

The UI also exposes router telemetry via `router_debug`.
