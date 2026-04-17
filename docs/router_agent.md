# Router Agent

Related docs:

- [IKMAS Overview](./IKMAS.md)
- [Architecture](./architecture.md)
- [Orchestrator](./orchestrator.md)
- [Roles](./roles.md)
- [Intent + Distance](./intent_distance.md)
- [Schema](./schema.md)

## Overview

The system now uses a **dedicated router agent** before the answering agent is selected.

Its task is:

- classify the request as a knowledge situation
- assign the most suitable agent role
- expose the routing decision for debugging

The router does **not** answer the user question directly.

---

## Core Responsibility

> Turn a raw user request into a **routing decision**.

The routing decision contains:

- `seci_mode`
- `reuse_situation`
- `selected_agent`
- `routing_confidence`
- `reason`
- `required_context`
- `verification_need`
- `next_state`

---

## Active Agent Set

Currently the system routes to **four active agents**:

- `ScribeAgent`
- `SemanticLinkingAgent`
- `MentorAgent`
- `ContextReconstructorAgent`

---

## Architecture Position

```
User Input
   ↓
Router Agent
   ↓
Route Decision
   ↓
Retrieval
   ↓
Prompt Construction
   ↓
Selected Role Agent
   ↓
Validation
   ↓
UI
```

---

## Router Logic

### 1. Router Prompt

The router is implemented as an LLM component with its own system prompt.

It classifies a request along two theoretical dimensions:

- SECI knowledge conversion mode
- knowledge reuse situation

---

### 2. Agent Registry

The router receives a small registry of available agents.

Each entry contains:

- agent name
- human-readable label
- supported SECI modes
- supported reuse situations
- core function

This keeps the routing decision explicit and extendable.

---

### 3. Structured Output

The router must return JSON matching `RouterPayload`.

Example structure:

```json
{
  "seci_mode": "Combination",
  "reuse_situation": "Secondary Knowledge Miner",
  "selected_agent": "ContextReconstructorAgent",
  "routing_confidence": "high",
  "reason": "The user needs missing context restored to continue work in a literature review.",
  "required_context": ["relevant papers", "previous review notes"],
  "verification_need": "user confirmation of relevance",
  "next_state": "agent_execution"
}
```

---

## Normalization Layer

LLM router outputs are not always schema-perfect.

Therefore the router pipeline normalizes common deviations before validation:

- human-readable agent labels → internal role ids
- numeric confidence → `low` / `medium` / `high`
- scalar `required_context` → list
- boolean `verification_need` → string

This reduces unnecessary fallback routing.

---

## Heuristic Fallback

If the router agent fails, the system falls back to a deterministic heuristic router.

Fallback reasons include:

- invalid JSON
- schema mismatch
- unsupported labels
- missing critical fields

The fallback still maps requests into the four active agents.

Special handling exists for:

- project documentation prompts → `ScribeAgent`
- semantic linking / synthesis prompts → `SemanticLinkingAgent`
- literature-context / re-entry prompts → `ContextReconstructorAgent`
- general explanation prompts → `MentorAgent`

---

## Current Role Mapping

### `ScribeAgent`

- primary use: externalization
- typical case: convert raw notes into reusable documentation

### `SemanticLinkingAgent`

- primary use: combination
- typical case: connect explicit artifacts and show relations

### `MentorAgent`

- primary use: explanation for novice understanding
- typical case: explain a concept in accessible language

### `ContextReconstructorAgent`

- primary use: restore missing context
- typical case: help the user re-enter a literature review or recover prior context

---

## UI Debug Output

The final assistant payload now includes `router_debug`.

The UI renders this inside a **Router Debug** expander.

Visible fields:

- selected role
- knowledge mode
- distance
- routing confidence
- fallback used or not
- reason
- required context
- verification need
- next state

This makes routing behavior inspectable per turn.

---

## Why this matters

The system no longer relies only on static role heuristics.

Instead it uses:

1. an LLM router for context-sensitive classification
2. a heuristic fallback for robustness
3. UI-visible routing telemetry for debugging

This makes routing:

- more transparent
- easier to debug
- closer to the multi-agent prototype described in the paper
