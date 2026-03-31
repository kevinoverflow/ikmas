# Orchestrator

## Overview

The orchestrator is the **central control unit** of the system.

It coordinates all components to transform a user input into a **validated, structured assistant response**.

---

## Core Responsibility

> Turn a raw user input into a **schema-valid, logged, context-aware response**.

---

## Architecture Position

```
User Input
   ↓
Orchestrator
   ↓
(Intent + Distance)
   ↓
Retrieval + Confidence
   ↓
Role Routing
   ↓
FSM (Tutoring only)
   ↓
Prompt Construction
   ↓
LLMClient (JSON / Repair / Fallback)
   ↓
Validation
   ↓
Persistence (SQLite)
   ↓
UI
```

---

## Entry Point

### `handle_turn(...)`

```
defhandle_turn(session_id:str,user_input:str,user_id:str|None=None) ->dict
```

This function executes a full system turn.

---

## Execution Pipeline

### 1. Session Initialization

```
create_session(session_id)
```

Ensures the session exists in the database.

---

### 2. Context Building

```
session_ctx=build_session_ctx(session_id)
user_profile=build_user_profile(user_id)
```

Currently placeholders.

Future use:

- session memory restoration
- personalization

---

### 3. Intent Classification

```
intent=classify_intent(user_input)
```

Examples:

- `what_is`
- `simplify`
- `project_specific`
- `learn_mode`

---

### 4. Knowledge Distance

```
distance=estimate_distance(user_input,intent)
```

Types:

- `ESN` → simple explanation
- `SWP` → project-specific
- `SWPr` → cross-context
- `SKM` → pattern mining

---

### 5. Retrieval + Confidence

```
retrieval=run_retrieval(user_input)
confidence=retrieval["confidence"]
```

Retrieval returns:

- chunks
- scoring metrics
- confidence

---

### 6. Role Routing

```
role=route_role(...)
```

Maps context → agent role:

- `MentorAgent`
- `TutoringAgent`
- `DigitalMemoryAgent`
- `ConceptMiningAgent`

---

### 7. FSM State Decision

```
state=decide_state(...)
```

Only active for:

- `TutoringAgent`
- or explicit learning mode

States:

- `ASSESS`
- `EXPLAIN`
- `CHECK`
- `PRACTICE`
- `FEEDBACK`
- `SCHEDULE`

---

### 8. Prompt Construction

```
prompt=build_prompt(...)
```

Includes:

- role
- state
- intent
- distance
- confidence
- retrieved context

---

### 9. LLM Call (Strict JSON)

```
payload=client.generate_json(prompt)
```

Handled by `LLMClient`:

- JSON enforcement
- schema validation
- repair attempt
- fallback if needed

---

### 10. Final Validation

```
AssistantPayload.model_validate(payload)
```

Guarantees:

- schema correctness
- structural consistency

---

### 11. Telemetry Enrichment

```
payload["telemetry"]["intent"]=intent
payload["telemetry"]["confidence"]=confidence
...
```

Adds orchestration metadata.

---

### 12. Turn Logging

```
log_turn(turn)
```

Stores:

- full JSON payload
- system state
- routing decisions
- confidence

---

### 13. Artefact Persistence

```
save_artefacts(...)
```

Stores:

- generated artefacts
- references to retrieval chunks

---

### 14. Return Response

```
returnpayload
```

Returned object is:

- schema-valid
- ready for UI rendering

---

## Prompt Structure

```
Du bist {role}.
Antworte ausschließlich als JSON entsprechend dem Schema.

Kontext:
- intent
- distance
- confidence
- state

Nutzeranfrage:
...

Retrieved Context:
...
```

---

## Data Flow

```
Input → Intent → Distance → Retrieval → Confidence
      → Role → State → Prompt → LLM
      → JSON → Validate → Store → Output
```

---

## Guarantees

After `handle_turn()`:

- Output is always valid JSON
- Output matches schema
- Turn is persisted
- Artefacts are stored
- Telemetry is complete

---

## Design Principles

### 1. Deterministic Pipeline

Every step is explicit and traceable.

---

### 2. Separation of Concerns

| Layer        | Responsibility     |
| ------------ | ------------------ |
| Retrieval    | data               |
| LLMClient    | output correctness |
| Orchestrator | decision logic     |

---

### 3. Fail-Safe Execution

- invalid LLM output → repair
- repair fails → fallback
- system never breaks

---

### 4. Observability

Every turn stores:

- full payload
- system state
- routing decisions

---

## Current Limitations

- no session memory restoration yet
- no long-term context usage
- no adaptive role tuning
- prompt is static (no templates yet)

---

## Future Extensions

- session context reconstruction
- adaptive prompting per role
- dynamic retrieval strategies
- multi-turn FSM memory
- learning schedule integration
