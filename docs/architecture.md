# Architecture

## Current Runtime

```text
User
  -> Streamlit UI
  -> Orchestrator
  -> Router Agent
  -> Retrieval + Reranking
  -> Role Prompt + LLM
  -> AssistantPayload validation
  -> Artifact reuse/generation
  -> SQLite persistence
  -> UI rendering
```

The implementation is centered on `app/backend/orchestrator.py`. The orchestrator coordinates routing, retrieval, role-prompted generation, artifact handling, and persistence for each chat turn.

## Major Components

| Component | Main files | Status |
|---|---|---|
| Streamlit UI | `app/ui/*` | Implemented |
| Authentication | `app/backend/auth.py`, `app/ui/auth.py` | Implemented |
| User workspace scoping | `app/backend/user_scope.py` | Implemented |
| Orchestrator | `app/backend/orchestrator.py` | Implemented |
| Router Agent | `app/backend/router_agent.py`, `app/prompts/router_agent_prompt.py` | Implemented |
| Active role prompts | `app/prompts/scribe_agent.py`, `semantic_linking_agent.py`, `mentor_agent.py`, `context_reconstructor_agent.py` | Implemented |
| Retrieval | `app/backend/retrieval.py`, `app/rag/*` | Implemented |
| Vector DB | `app/rag/vectorstore.py`, `data/chroma/` | Implemented |
| LLM layer | `app/rag/llm.py`, `app/backend/llm_client.py` | Implemented |
| Artifact system | `app/backend/artifact_*`, `app/backend/artifact_generators/*`, `app/ui/artifacts.py` | Partially implemented |
| SQLite persistence | `app/backend/sqlite_store.py` | Implemented |
| Tutor FSM | `app/backend/fsm.py` | Scaffolded, not active in normal routing |
| Full 16-agent matrix | docs/planning only | Planned |

## Important Runtime Boundaries

- The UI does not call the LLM directly. It calls `handle_turn(...)`.
- The orchestrator does not answer with free-form text. It requires `AssistantPayload`.
- The router does not answer user questions. It only classifies and plans.
- Retrieval returns normalized chunk dictionaries so prompts, citations, and artifact generation share one context format.
- Artifacts are stored in SQLite, not Chroma. Chroma stores source-document chunks.

## Data Stores

- `data/uploads/<collection_id>/`: uploaded source files.
- `data/chroma/`: persistent Chroma vector data.
- `data/ikmas.db`: users, auth sessions, chat sessions, turns, artifacts, links, concepts, user knowledge, session history.

## Implementation Caveats

- The code uses both `artifact` and `artefact`; database tables and schema fields often use `artefact`.
- `role_router.py` is a deterministic helper/fallback matrix, but `handle_turn(...)` uses the LLM router in `router_agent.py`.
- The current FSM only returns tutor states for `TutoringAgent` or forced tutor mode. `TutoringAgent` is not in the active `RoleName` set.
