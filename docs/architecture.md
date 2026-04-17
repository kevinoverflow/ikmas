# Architecture

Related docs:

- [IKMAS Overview](./IKMAS.md)
- [Orchestrator](./orchestrator.md)
- [Router Agent](./router_agent.md)
- [Roles](./roles.md)
- [System Flow](./system_flow.md)

## Core Idea

System adapts to knowledge reuse situations through a routed multi-agent architecture.

## Pipeline

1. Intent
2. Router Agent
3. Role Selection
4. Retrieval
5. Prompt Construction
6. LLM
7. Validation
8. UI Debug Output

## Why this matters

Traditional RAG fails when context is missing.
We inject context via roles and make routing transparent through router debug data.
