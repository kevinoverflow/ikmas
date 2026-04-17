# IKMAS

## What is this?

Role-based RAG system with:

- [Orchestrator](./orchestrator.md)
- [Router Agent](./router_agent.md)
- [Knowledge Distance (Markus)](./intent_distance.md)
- [SECI-oriented role selection](./roles.md)
- [Structured JSON output](./schema.md)
- Router Debug in UI

## Architecture

User → [Orchestrator](./orchestrator.md) → [Router Agent](./router_agent.md) → [Role](./roles.md) → [Retrieval](./retrieval.md) → [LLM](./llm.md) → [JSON](./schema.md) → UI

Related system views:

- [Architecture](./architecture.md)
- [System Flow](./system_flow.md)
- [SQLite Persistence](./sqlite.md)
- [Design Decisions](./decisions.md)

## Roles

- [ScribeAgent / SemanticLinkingAgent / MentorAgent / ContextReconstructorAgent](./roles.md)

## Main Entry Points

- [IKMAS Overview](./IKMAS.md)
- [Orchestrator](./orchestrator.md)
- [Router Agent](./router_agent.md)
- [Roles](./roles.md)
- [Intent + Distance](./intent_distance.md)
- [Retrieval](./retrieval.md)
- [LLM / JSON Handling](./llm.md)
- [Schema](./schema.md)
- [Architecture](./architecture.md)
- [System Flow](./system_flow.md)

## Recommended Reading Order

1. [IKMAS Overview](./IKMAS.md)
2. [Architecture](./architecture.md)
3. [Orchestrator](./orchestrator.md)
4. [Router Agent](./router_agent.md)
5. [Roles](./roles.md)
6. [Intent + Distance](./intent_distance.md)
7. [Retrieval](./retrieval.md)
8. [LLM](./llm.md)
9. [Schema](./schema.md)
