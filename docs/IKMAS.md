# IKMAS Documentation Index

IKMAS is currently a Streamlit RAG application with authenticated workspaces, Chroma retrieval, an LLM router, four active role prompts, structured JSON responses, a small artifact generation system, and SQLite persistence.

The codebase also contains research-oriented scaffolding for a larger SECI x Markus multi-agent system. This documentation separates implemented runtime behavior from planned architecture.

## Recommended Reading Order

1. [Architecture](./architecture.md)
2. [Orchestrator](./orchestrator.md)
3. [Router Agent](./router_agent.md)
4. [Retrieval](./retrieval.md)
5. [Artifact System](./artifact_system.md)
6. [SQLite Persistence](./sqlite.md)
7. [Schema](./schema.md)
8. [Roles](./roles.md)
9. [System Flow](./system_flow.md)

## Runtime Components

- [Architecture](./architecture.md): end-to-end component map and implementation status.
- [Orchestrator](./orchestrator.md): `handle_turn(...)` pipeline.
- [Router Agent](./router_agent.md): LLM classification and route normalization.
- [Retrieval](./retrieval.md): file ingestion, Chroma, reranking, confidence scoring.
- [Artifact System](./artifact_system.md): artifact reuse, generation, persistence, and UI actions.
- [SQLite Persistence](./sqlite.md): database schema and storage APIs.
- [LLM](./llm.md): OpenAI-compatible backend and strict JSON handling.
- [File Handling](./file_handling.md): upload storage and indexing controls.
- [FSM](./fsm.md): tutor-state helper and current limitations.

## Theory and Planning

- [Roles](./roles.md): active roles plus planned role matrix.
- [Intent Distance](./intent_distance.md): legacy heuristic classifier and current role in the project.
- [Design Decisions](./decisions.md): implemented architectural decisions.
- [Model Configuration](./model_configuration.md): environment variables and defaults.
- [Model Use Case Matrix](./model_use_case_matrix.md): local/provider model notes.

Historical proposals and migration-era notes live in [archive](./archive/). They are preserved for context, but the implementation-first docs above should be treated as current.
