# AGENTS.md

## Project Overview

IKMAS (Intelligent Knowledge Management Assistance System) is a RAG-based multi-agent system implementing 16 theoretically grounded GenAI roles. The roles are derived from the intersection of **Nonaka & Takeuchi's SECI model** (knowledge conversion modes) and **Markus' typology** (knowledge reuse situations). The system routes user requests to role-specific LLM agents via a state-machine-based orchestrator. It runs as a Streamlit application with ChromaDB vector storage and SQLite conversation persistence.

> **Implementation status legend used throughout this document**
> - ✅ Implemented
> - 🔲 Planned — not yet implemented

---

## Key Commands

```bash
./run.sh                                    # Main startup (handles venv + Streamlit)
./run_tests.sh                              # Run full test suite
pip install -r requirements.txt             # Manual dependency install
streamlit run app/ui/streamlit_app.py       # Run UI directly
```

---

## Environment Setup

- **Python**: 3.11
- **LLM API Key**: Set `SCADS_API_KEY` (or `OPENAI_API_KEY` as fallback)
- **Tracing** (optional): Set `LANGSMITH_API_KEY` for LangSmith tracing
- **Virtual environment**: `.venv` — managed automatically by `run.sh`

---

## Project Structure

```
app/
├── backend/
│   ├── fsm.py                    # ✅ Finite state machine (states S0–S7)
│   ├── orchestrator.py           # ✅ Top-level conversation controller
│   ├── role_router.py            # ✅ Maps (SECI, reuse_situation) → agent name
│   ├── router_agent.py           # ✅ LLM-based request classifier
│   ├── retrieval.py              # ✅ RAG retrieval coordination
│   ├── llm_client.py             # ✅ LLM API wrapper
│   ├── intent_distance.py        # ✅ Intent/context distance scoring
│   ├── sqlite_store.py           # ✅ Conversation persistence (ikmas.db)
│   └── validation.py             # ✅ Input/output validation
├── domain/
│   ├── schema.py                 # ✅ Pydantic models (RouterOutput, AgentOutput, …)
│   └── types.py                  # ✅ Enums: SECIMode, ReuseSituation, AgentName, FSMState
├── infrastructure/
│   ├── config.py                 # ✅ Environment, model, path configuration
│   └── tracing.py                # ✅ LangSmith integration
├── prompts/
│   ├── router_agent_prompt.py    # ✅ Router system prompt
│   ├── scribe_agent.py           # ✅ Scribe Agent prompt
│   ├── semantic_linking_agent.py # ✅ Semantic Linking Agent prompt
│   ├── mentor_agent.py           # ✅ Mentor Agent prompt
│   ├── context_reconstructor_agent.py  # ✅ Context Reconstructor Agent prompt
│   └── prompts.py                # ✅ Prompt registry / loader
├── rag/
│   ├── ingest.py                 # ✅ Document ingestion pipeline
│   ├── vectorstore.py            # ✅ ChromaDB wrapper
│   ├── retriever.py              # ✅ Retrieval logic
│   ├── reranker.py               # ✅ Result reranking
│   ├── llm.py                    # ✅ RAG-specific LLM calls
│   ├── storage.py                # ✅ File storage helpers
│   └── tokenizer.py              # ✅ Tokenizer (Qwen3-Embedding-4B)
└── ui/
    └── streamlit_app.py          # ✅ Entry point

data/
├── chroma/                       # ✅ ChromaDB vector embeddings
├── uploads/default/              # ✅ Uploaded source documents
└── ikmas.db                      # ✅ SQLite conversation store

docs/                             # ✅ Architecture decision records + module docs
tests/                            # ✅ Pytest suite (mirrors app/ structure)
tokenizers/Qwen3-Embedding-4B/    # ✅ Local embedding tokenizer
```

---

## Theoretical Foundation

### SECI Knowledge Conversion Modes
| Mode | Description |
|---|---|
| Socialization | tacit → tacit (experience sharing, situated advice) |
| Externalization | tacit → explicit (documentation, structuring implicit knowledge) |
| Combination | explicit → explicit (synthesis, linking, comparing artifacts) |
| Internalization | explicit → tacit (learning, reflection, guided practice) |

### Markus Knowledge Reuse Situations
| Situation | Description |
|---|---|
| Shared Work Producer | Reuses own or team's prior knowledge |
| Shared Work Practitioner | Reuses knowledge from peers in similar roles |
| Expertise-Seeking Novice | Needs to understand expert knowledge outside own domain |
| Secondary Knowledge Miner | Reuses knowledge created for a different purpose or distant context |

---

## Agent Registry (Full 4×4 Matrix)

The `role_router.py` maps each `(SECIMode, ReuseSituation)` pair to exactly one agent. Agents marked ✅ are fully implemented with prompts in `app/prompts/`. The remaining 12 share the same configuration template and can be added incrementally.

| SECI \ Markus | Shared Work Producer | Shared Work Practitioner | Expertise-Seeking Novice | Secondary Knowledge Miner |
|---|---|---|---|---|
| **Socialization** | Digital Memory Agent | Expert Proxy Agent | ✅ Mentor Agent | Synthetic Expert Agent |
| **Externalization** | ✅ Scribe Agent | Context Elicitation Agent | Problem Formulation Agent | Cross-Context Reframing Agent |
| **Combination** | ✅ Semantic Linking Agent | Synthesis Linker Agent | Adaptive Curator Agent | Concept Mining Agent |
| **Internalization** | Personal Context Restoration Agent | Experience Simulation Agent | Tutoring Agent | Ideation Trigger Agent |

> **Note**: The Mentor Agent spans Socialization/Internalization; the Context Reconstructor Agent spans Internalization/Combination. Both are implemented as prototype agents despite covering two SECI modes.

---

## ✅ Implemented Agents (Prototype)

### ✅ Scribe Agent — `app/prompts/scribe_agent.py`
- **SECI**: Externalization | **Reuse**: Shared Work Producer
- **Function**: Transforms fragmented work traces (notes, transcripts, chat excerpts) into structured, reusable knowledge artifacts.
- **Required inputs**: raw notes/transcript, intended document type, target audience, reuse purpose
- **Output format**: Summary · Background · Key Decisions · Rationale · Open Issues · Action Items · Reuse Notes
- **Key constraint**: Must not invent missing information. Inferred context must be labeled as interpretation. Uncertain elements require user confirmation before finalizing.

### ✅ Semantic Linking Agent — `app/prompts/semantic_linking_agent.py`
- **SECI**: Combination | **Reuse**: Shared Work Producer
- **Function**: Identifies semantic relations between explicit knowledge artifacts — beyond keyword overlap, focusing on conceptual similarity, dependencies, and contradictions.
- **Required inputs**: one or more documents/excerpts, synthesis goal, desired granularity
- **Output format**: Identified concepts · Related artifacts · Semantic relations · Redundancies · Contradictions · Missing links · Suggested tags/graph nodes
- **Key constraint**: Every proposed link must be justified through conceptual or contextual reasoning, not surface-level keyword matching.

### ✅ Mentor Agent — `app/prompts/mentor_agent.py`
- **SECI**: Socialization / Internalization | **Reuse**: Expertise-Seeking Novice
- **Function**: Translates expert knowledge into accessible language for domain outsiders while preserving technical accuracy. Uses progressive explanation and reflective questioning.
- **Required inputs**: user question, domain/artifact to explain, user's prior knowledge level, desired depth
- **Output format**: Plain-language explanation · Key concepts · Practical example · Common misunderstandings · Reflection question · Suggested next step
- **Key constraint**: Must not replace expert judgment in high-risk domains. Must flag uncertainty and recommend expert validation when needed.

### ✅ Context Reconstructor Agent — `app/prompts/context_reconstructor_agent.py`
- **SECI**: Internalization / Combination | **Reuse**: Secondary Knowledge Miner
- **Function**: Reconstructs the background, assumptions, constraints, and transfer conditions of an artifact created for a different context or purpose.
- **Required inputs**: artifact to interpret, user's target context, reuse purpose, available metadata
- **Output format**: Artifact summary · Reconstructed original context · Assumptions · Conditions of applicability · Transferability assessment · Risks of reuse · Questions for validation
- **Key constraint**: Reconstructed elements must be labeled by confidence level. Must distinguish evidence-based reconstruction from plausible interpretation. Never treat reconstruction as historical fact.

---

## 🔲 Planned: Operational Agent Roles (not yet implemented)

These agents correspond to the "Virtuelle Mitarbeiter" concept from the system design. They map onto the SECI phases as pipeline stages rather than on-demand roles, and are not yet connected to the routing matrix.

### 🔲 Silent Scribe
- **SECI phase**: Socialization
- **Function**: Passive meeting capture — records audio/video, stores transcripts, extracts decisions and action items automatically with no active user interaction required.
- **Outputs**: raw transcript, extracted decisions JSON, action items list, indexed meeting record
- **Planned integrations**: Meeting Recorder addon, Slack/Matrix/Discord bot, Chrome Extension

### 🔲 Knowledge Interviewer
- **SECI phase**: Externalization
- **Function**: Active system interview after a meeting or work session. Extracts decision rationale, makes implicit knowledge explicit, produces structured artifacts.
- **Interaction pattern**: Asks targeted follow-up questions (max 3–5), requests missing evidence, then generates artifacts.
- **Outputs**: Decision Record · Case Card · FAQ · SOP Draft → stored in Knowledge Base

### 🔲 Curator / Synthesizer
- **SECI phase**: Combination
- **Function**: Consolidates the Knowledge Base — clusters documents, detects duplicates, flags contradictions, generates master summaries, builds glossary and prerequisite structures, generates Cases and Quiz Items.
- **Outputs**: merged/deduped document set, contradiction warnings, master summaries, glossary, prerequisite graph, case cards, quiz items

### 🔲 Tutor Agent (with internal FSM)
- **SECI phase**: Internalization
- **Function**: Drives an interactive learning loop for a specific knowledge topic. Manages its own sub-FSM independently of the main SECI FSM.
- **Internal FSM states**:

  | State | Description |
  |---|---|
  | `ASSESS` | 2–3 diagnostic questions to gauge current knowledge distance |
  | `EXPLAIN` | Explanation + example + organizational context |
  | `CHECK` (Teach-Back) | "Explain it back to me in your own words" |
  | `PRACTICE` | Quiz question or mini scenario |
  | `FEEDBACK` | Rubric-based feedback + reasoning + source citations |
  | `SCHEDULE` | Spaced repetition scheduling |

- **Inputs**: topic/artifact from Knowledge Base, User Model (knowledge distance, learning progress, goals, review schedule)
- **Key constraint**: Must use structured Knowledge Layer artifacts (concepts, definitions, prerequisites, pitfalls, cases, quiz items) — not free-form retrieval alone.

### 🔲 Simulation Agent
- **SECI phase**: Internalization (transfer)
- **Function**: Case-based training through decision scenarios and transfer exercises. Presents realistic organizational situations and evaluates user decisions.
- **Outputs**: scenario description, decision options, consequence feedback, transfer assessment

---

## 🔲 Planned: Structured Knowledge Layer

The Knowledge Base currently stores raw document chunks in ChromaDB. The planned Structured Knowledge Layer adds a dedicated artifact store with typed entries, enabling the Tutor and Simulation agents to work from structured learning objects rather than raw retrieval.

### Artifact Types

| Type | Description |
|---|---|
| **Concept** | Core definition of a domain term or idea |
| **Definition** | Formal/precise formulation of a concept |
| **Prerequisite** | Dependency graph: what must be known before this |
| **Pitfall** | Common misunderstandings or failure modes |
| **Case** | Real or constructed organizational scenario |
| **Quiz Item** | Question + answer + evidence reference |

### User Model Store (planned)

Tracks per-user learning state to enable adaptive routing:

| Field | Description |
|---|---|
| `knowledge_distance` | Computed distance between user's known concepts and target topic |
| `learning_progress` | Which artifacts/topics have been covered |
| `knowledge_goals` | User-defined or system-inferred learning targets |
| `review_schedule` | Spaced repetition due dates |

The Role Router will use the User Model as an additional input dimension alongside user intent, retrieval confidence, and SECI classification — enabling it to select between Tutor, Mentor, Simulation, and Curator roles based on the user's actual knowledge state.

---

## 🔲 Planned: SECI Pipeline Flow

The full system envisions a four-phase pipeline triggered by organizational events (e.g. a meeting):

**Phase 1 — Socialization** (Silent Scribe): Meeting recorded → transcript stored → decisions and action items extracted → no active user interaction.

**Phase 2 — Externalization** (Knowledge Interviewer): System interview → decision rationale secured → implicit knowledge made explicit → artifacts (Decision Record, Case Card, FAQ, SOP Draft) written to Knowledge Base.

**Phase 3 — Combination** (Curator/Synthesizer): Documents clustered → duplicates removed → contradictions flagged → master summaries generated → glossary and prerequisite structure built → Cases and Quiz Items created → Knowledge Base made learnable.

**Phase 4 — Internalization** (Tutor / Simulation): User enters learning loop via Tutor FSM (Assess → Explain → Check → Practice → Feedback → Schedule) or Simulation Agent for transfer training.

---

## Agent Configuration Template

Every agent prompt file in `app/prompts/` follows this structure. Use it when adding new agents:

```
Agent Name:
Theoretical Anchor:         (SECI mode + Markus situation)
Primary Knowledge Function:
User Situation:
Task Objective:
Required Inputs:
Optional Inputs:
Interaction Pattern:
Output Format:
Verification Routine:
Limitations:
Escalation Condition:
```

---

## Router (`app/backend/router_agent.py`)

The router is a dedicated LLM component that **classifies requests — it does not answer them**. It delegates to the appropriate agent via `role_router.py`.

**Classification dimensions**:
1. SECI knowledge conversion mode
2. Knowledge reuse situation
3. Expected knowledge support need (documentation, explanation, linking, reconstruction, …)

**Router output schema** (JSON only — defined in `app/domain/schema.py`):
```json
{
  "seci_mode": "Externalization",
  "reuse_situation": "Shared Work Producer",
  "selected_agent": "Scribe Agent",
  "routing_confidence": "high | medium | low",
  "reason": "...",
  "missing_information": [],
  "required_context": [],
  "verification_need": "...",
  "next_state": "context_enrichment | agent_execution"
}
```

The router system prompt lives in `app/prompts/router_agent_prompt.py`.

---

## State Machine (`app/backend/fsm.py`)

The main FSM controls conversation flow. State transitions depend on classification completeness, missing context, and verification requirements.

| State | Description |
|---|---|
| S0 `USER_REQUEST_INTAKE` | Receive and parse user request |
| S1 `CONTEXT_ENRICHMENT` | Ask one targeted clarification if routing context is insufficient |
| S2 `THEORETICAL_CLASSIFICATION` | Router classifies SECI mode + reuse situation |
| S3 `AGENT_SELECTION` | Map classification to agent registry |
| S4 `AGENT_EXECUTION` | Selected agent processes request per its configuration |
| S5 `VERIFICATION` | Flag uncertain elements; request user confirmation where needed |
| S6 `HANDOVER_OR_ITERATION` | Route to second agent or iterate (e.g., Scribe → Semantic Linking) |
| S7 `END` | Deliver final output |

S1 is skipped when sufficient context is already present. S6 enables chained workflows, e.g. Context Reconstructor → Mentor Agent when a reconstructed concept needs explanation.

> 🔲 The Tutor Agent will run its own **nested FSM** (Assess → Explain → Check → Practice → Feedback → Schedule) independently of the main SECI FSM. This sub-machine is not yet implemented.

---

## RAG Pipeline (`app/rag/`)

1. **Ingestion** (`ingest.py`): documents uploaded to `data/uploads/default/` are chunked and embedded.
2. **Embedding**: Qwen3-Embedding-4B tokenizer (local at `tokenizers/`) + embedding model via API.
3. **Vector store** (`vectorstore.py`): ChromaDB at `data/chroma/`.
4. **Retrieval** (`retriever.py`): retrieves relevant chunks per agent request.
5. **Reranking** (`reranker.py`): reranks results before injection into agent context.

Retrieved context is injected into the agent prompt at S4 execution time.

> 🔲 The planned Structured Knowledge Layer will extend retrieval with typed artifact lookups (Concept, Case, Quiz Item, etc.) in addition to vector search.

---

## Persistence (`app/backend/sqlite_store.py`)

Conversation turns are persisted to `data/ikmas.db` (SQLite). History is available within and across sessions. Schema is defined in `app/domain/schema.py`.

> 🔲 The User Model Store (knowledge distance, learning progress, review schedule) will be added as additional tables in `ikmas.db`.

---

## Routing Examples

```json
// "Turn these meeting notes into a reusable project decision document"
{ "seci_mode": "Externalization", "reuse_situation": "Shared Work Producer",
  "selected_agent": "Scribe Agent", "next_state": "context_enrichment" }

// "I found old support tickets and want to identify product improvement ideas"
{ "seci_mode": "Combination", "reuse_situation": "Secondary Knowledge Miner",
  "selected_agent": "Concept Mining Agent", "next_state": "agent_execution" }

// "I don't understand this legal guideline — what does it mean for our project?"
{ "seci_mode": "Internalization", "reuse_situation": "Expertise-Seeking Novice",
  "selected_agent": "Tutoring Agent", "next_state": "context_enrichment" }
```

---

## Adding a New Agent

1. Create `app/prompts/<agent_name>.py` using the configuration template above.
2. Register the prompt in `app/prompts/prompts.py`.
3. Add the `(SECIMode, ReuseSituation)` → `AgentName` mapping in `app/backend/role_router.py`.
4. Add the agent name to the `AgentName` enum in `app/domain/types.py`.
5. Add tests in `tests/test_role_router.py` and `tests/test_<agent_name>.py`.
6. The FSM and orchestrator require no changes.

---

## Testing

```bash
./run_tests.sh          # Full suite via pytest
```

| Test file | Covers |
|---|---|
| `test_fsm.py` | State transitions and guard conditions |
| `test_role_router.py` | (SECI, Reuse) → agent name mapping |
| `test_orchestrator.py` | End-to-end conversation flow |
| `test_retriever.py` | RAG retrieval correctness |
| `test_reranker.py` | Reranking logic |
| `test_ingest.py` | Document ingestion pipeline |
| `test_llm_client.py` | LLM client wrapper |
| `test_intent_distance.py` | Intent/context distance scoring |
| `test_schema.py` | Pydantic schema validation |
| `test_storage.py` | File and SQLite storage |
| `test_validation.py` | Input/output validation |

---

## Documentation

Extended module-level docs live in `docs/`:

| File | Content |
|---|---|
| `architecture.md` | System overview and component relationships |
| `fsm.md` | State machine design and transition table |
| `orchestrator.md` | Orchestrator flow and session management |
| `router_agent.md` | Router prompt design and classification logic |
| `roles.md` | Full 16-agent role descriptions |
| `retrieval.md` | RAG pipeline details |
| `intent_distance.md` | Intent distance algorithm |
| `schema.md` | Domain model and Pydantic schemas |
| `sqlite.md` | Persistence layer |
| `llm.md` | LLM client configuration |
| `system_flow.md` | End-to-end request lifecycle |
| `decisions.md` | Architecture decision records (ADRs) |
| `IKMAS.md` | Project-level overview |
