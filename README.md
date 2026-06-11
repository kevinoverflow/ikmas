# IKMAS

IKMAS is an implementation-first RAG application for knowledge management. It runs as a Streamlit app with authenticated user workspaces, file upload and indexing, ChromaDB retrieval, LLM-based routing, role-specific prompting, structured JSON responses, generated knowledge artifacts, and SQLite persistence.

The theoretical basis is the SECI knowledge-conversion model and Markus' knowledge-reuse situations, but the current repository implements a smaller production path than the full 4 x 4 role matrix. The active runtime routes to four role prompts and can generate three structured artifact types.

## Current Runtime Architecture

```text
User
  -> Streamlit UI
  -> app.backend.orchestrator.handle_turn()
  -> Router Agent
  -> Chroma retrieval + reranking
  -> role prompt + retrieved context
  -> OpenAI-compatible chat backend
  -> structured JSON validation/repair/fallback
  -> artifact reuse and artifact subagents
  -> SQLite persistence
  -> Streamlit chat + artifact browser
```

## Implemented Today

- Streamlit UI with login/registration, remembered auth sessions, user-scoped workspaces, chat, file workspace, indexing controls, session history, and artifact browser.
- File storage under `data/uploads/<collection_id>/` with filename sanitization, hash dedupe, conflict handling, download, and delete.
- Ingestion for PDF, TXT, Markdown, DOCX, PPTX, PNG, JPG/JPEG, and WEBP files.
- ChromaDB vector storage under `data/chroma/`.
- Retrieval pipeline: similarity search, external rerank endpoint, confidence scoring, citation chunk formatting.
- LLM router agent that classifies SECI mode, reuse situation, active role, routing confidence, context requirements, and artifact generation plans.
- Active role prompts: `ScribeAgent`, `SemanticLinkingAgent`, `MentorAgent`, `ContextReconstructorAgent`.
- Structured assistant contract in `app/domain/schema.py`, with parse, normalize, repair, salvage, and deterministic fallback logic.
- Artifact reuse and generation for `definition`, `concept`, and `quiz_item` artifacts.
- SQLite persistence for users, auth sessions, sessions, turns, artifacts, links, concepts, user knowledge, and session history.
- Optional LangSmith tracing.

## Partially Implemented

- Session awareness reads recent `session_history` rows and injects recurring routing themes and related sessions into the router. Embedding-based similarity and knowledge-gap extraction are placeholders.
- Tutor FSM states exist in `app/backend/fsm.py`, but no `TutoringAgent` is registered in the active role set, so normal turns usually have `state = None`.
- `concepts` and `user_knowledge` tables exist, but the adaptive learning/user-model layer is not wired into orchestration.
- `ArtifactType` includes future types such as `prerequisite`, `pitfall`, and `case`, but only `definition`, `concept`, and `quiz_item` have executable generators.
- `role_router.py` contains a small deterministic role matrix, but the main orchestrator currently uses the LLM router in `router_agent.py`.

## Planned / Not Implemented

- Full 16-agent SECI x Markus matrix.
- Silent Scribe, Knowledge Interviewer, Curator/Synthesizer, Tutor Agent, and Simulation Agent.
- Event-driven SECI pipeline for meetings and organizational workflows.
- Structured prerequisite graph, pitfalls, cases, spaced repetition scheduling, and mastery updates in the active UI flow.

## Requirements

- Python 3.11
- `SCADS_API_KEY` or `OPENAI_API_KEY`
- Optional: `LANGSMITH_API_KEY` and `LANGSMITH_TRACING=true`

Default provider configuration lives in `app/infrastructure/config.py`:

- `OPENAI_BASE_URL` defaults to `https://llm.scads.ai/v1`
- chat model defaults to `Qwen/Qwen3-Coder-30B-A3B-Instruct`
- embedding model defaults to `Qwen/Qwen3-Embedding-4B`
- rerank model defaults to `BAAI/bge-reranker-v2-m3`

## Run

```bash
./run.sh
```

Manual startup:

```bash
pip install -r requirements.txt
streamlit run app/ui/streamlit_app.py
```

Run tests:

```bash
./run_tests.sh
```

## Repository Map

```text
app/backend/          orchestration, router, FSM helper, persistence, auth, artifact system
app/domain/           Pydantic schemas and shared dataclass/type contracts
app/infrastructure/   config and tracing
app/prompts/          router and active role prompts
app/rag/              storage, extraction, chunking, Chroma, retrieval, reranking, OCR/vision
app/ui/               Streamlit UI modules
docs/                 implementation-first architecture documentation
docs/archive/         historical proposals, summaries, and implementation notes
scripts/              ad hoc demos and diagnostics; not the main test suite
tests/                pytest coverage for backend, RAG, UI helpers, and artifact behavior
tokenizers/           local Qwen3 embedding tokenizer files
```

Start with [docs/IKMAS.md](docs/IKMAS.md), then [docs/architecture.md](docs/architecture.md), [docs/orchestrator.md](docs/orchestrator.md), and [docs/artifact_system.md](docs/artifact_system.md).

## License

Copyright (c) 2026 Kevin Hoang

IKMAS is licensed under the Apache License, Version 2.0.

You may obtain a copy of the License at:

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.

See the [LICENSE](LICENSE) file for the full license text.

Third-party software components remain subject to their respective licenses.
