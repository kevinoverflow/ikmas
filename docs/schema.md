# Assistant JSON Schema (Backend Contract)

Related docs:

- [IKMAS Overview](./IKMAS.md)
- [Orchestrator](./orchestrator.md)
- [Router Agent](./router_agent.md)
- [LLM](./llm.md)

This document describes the structured JSON contract used between the LLM, backend, and UI.

All responses must conform to this schema. No additional fields are allowed.

---

## Overview

The system does not return plain text responses.

Instead, every response is a structured JSON object that is:

- deterministic
- UI-renderable
- persistable
- debuggable

---

## Root Object: AssistantPayload

```
{
  "role":"...",
  "state":"... | null",
  "assistant_message":"...",
  "questions": [...],
  "artefacts": [...],
  "actions": [...],
  "citations": [...],
  "telemetry": {...},
  "router_debug": {...} | null
}
```

---

## Fields

### role

Defines the active system role.

Possible values:

- `ScribeAgent`
- `SemanticLinkingAgent`
- `MentorAgent`
- `ContextReconstructorAgent`

---

### state

Currently optional and usually `null`.

The FSM still exists in code, but the current active routed role set does not depend on it.

Possible values:

- `ASSESS`
- `EXPLAIN`
- `CHECK`
- `PRACTICE`
- `FEEDBACK`
- `SCHEDULE`

Otherwise: `null`

---

### assistant_message

Main textual response shown to the user.

---

### questions

Structured follow-up questions for user interaction.

Example:

```
{
  "id":"q1",
  "type":"text",
  "label":"Question text",
  "options": [],
  "required":true
}
```

Allowed question types:

- `text`
- `single_choice`
- `multi_choice`

Field meanings:

- `id`: unique identifier for the question
- `type`: UI rendering type
- `label`: text shown to the user
- `options`: selectable options for choice-based questions
- `required`: whether the user must answer

---

### artefacts

Generated knowledge outputs that can be stored or rendered in the UI.

Example:

```
{
  "type":"summary",
  "title":"Recap of Topic X",
  "content":"Text content",
  "concept_ids": [1,2]
}
```

Allowed artefact types:

- `summary`
- `flashcards`
- `quiz`
- `checklist`
- `note`
- `concept_map`

Field meanings:

- `type`: artefact category
- `title`: display title
- `content`: actual artefact content
- `concept_ids`: optional references to concept entities

---

### actions

System-level actions triggered by the response.

Example:

```
{
  "type":"store_artefact",
  "payload": {}
}
```

Allowed action types:

- `ask`
- `store_artefact`
- `schedule_review`
- `update_mastery`
- `none`

Field meanings:

- `type`: action identifier
- `payload`: additional action data

---

### citations

References to retrieved knowledge chunks.

Example:

```
{
  "source":"document.pdf",
  "chunk_id":"abc123",
  "title":"Optional title",
  "locator":"Page 12"
}
```

Field meanings:

- `source`: source document or collection
- `chunk_id`: retrieval chunk identifier
- `title`: optional human-readable source title
- `locator`: optional position reference such as page number

---

### telemetry

Debug and system metadata.

Example:

```
{
  "intent":"simplify",
  "distance":"ESN",
  "confidence":0.82,
  "retrieval_count":5,
  "repair_used":false,
  "fallback_used":false
}
```

Field meanings:

- `intent`: classified user intent
- `distance`: estimated knowledge distance
- `confidence`: retrieval confidence score
- `retrieval_count`: number of retrieved chunks
- `repair_used`: whether JSON repair was needed
- `fallback_used`: whether fallback output was used

---

### router_debug

Optional routing debug information attached by the orchestrator.

Example:

```
{
  "role":"ContextReconstructorAgent",
  "knowledge_mode":"INTERNALIZATION",
  "distance":"SKM",
  "routing_confidence":"high",
  "reason":"The user needs missing context restored to continue work in a literature review.",
  "required_context":["relevant papers","previous summaries"],
  "verification_need":"user confirmation of relevance",
  "next_state":"agent_execution",
  "used_fallback":false
}
```

Field meanings:

- `role`: routed agent
- `knowledge_mode`: routed knowledge mode
- `distance`: routed reuse distance
- `routing_confidence`: router confidence
- `reason`: human-readable routing explanation
- `required_context`: context the router expects
- `verification_need`: expected user validation need
- `next_state`: next execution state
- `used_fallback`: whether heuristic fallback was used

---

## Validation Rules

- All top-level fields are required.
- No additional properties are allowed.
- Output must be valid JSON.
- No markdown or explanatory text may appear outside the JSON payload in actual model output.
- Schema validation is enforced after generation.
- One repair attempt is allowed if validation fails.
- If repair also fails, a deterministic fallback payload is returned.

---

## Purpose

This schema enables:

- deterministic LLM output
- structured UI rendering
- persistent logging in SQLite
- role-based behavior
- router transparency via `router_debug`
- traceable retrieval through citations

---

## Summary

`AssistantPayload` is the central response contract of the system.

Everything flows through it:

- logic via role and state
- interaction via questions
- knowledge output via artefacts
- traceability via citations
- observability via telemetry
