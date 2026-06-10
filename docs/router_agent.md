# Router Agent

The router agent is implemented in `app/backend/router_agent.py` with its system prompt in `app/prompts/router_agent_prompt.py`.

The router classifies a user request; it does not answer the request.

## Active Output Contract

The LLM router returns `RouterPayload`:

```json
{
  "seci_mode": "Socialization | Externalization | Combination | Internalization",
  "reuse_situation": "Shared Work Producer | Shared Work Practitioner | Expertise-Seeking Novice | Secondary Knowledge Miner",
  "selected_agent": "ScribeAgent | SemanticLinkingAgent | MentorAgent | ContextReconstructorAgent",
  "routing_confidence": "low | medium | high",
  "reason": "...",
  "required_context": [],
  "verification_need": "...",
  "next_state": "...",
  "artifact_generation_plan": {
    "artifacts_needed": ["definition", "concept", "quiz_item"],
    "target_audience": "general",
    "reason": "..."
  }
}
```

The payload is normalized into `RouteDecision`, which uses internal labels:

- `knowledge_mode`: `SOCIALIZATION`, `EXTERNALIZATION`, `COMBINATION`, `INTERNALIZATION`
- `distance`: `SWP`, `SWPr`, `ESN`, `SKM`
- `role`: one of the active `RoleName` values

## Active Agents

- `ScribeAgent`
- `SemanticLinkingAgent`
- `MentorAgent`
- `ContextReconstructorAgent`

No other role is currently accepted by `RoleName` or `RouterPayload.selected_agent`.

## Session Awareness

If `user_id` is present, `route_with_agent(...)` calls `get_relevant_history(...)` and injects recent session data into the router prompt:

- recurring route themes from previous classifications
- related recent sessions with title, query, generated artifact names, and citation ids

Current limitations:

- `uncaptured_themes` is always empty.
- `session_embedding` is not used for semantic similarity.
- `get_session_similarity_score(...)` is a simple `difflib` helper, not part of the main router path.

## Artifact Plan Normalization

`normalize_artifact_generation_plan(...)` accepts only:

- `definition`
- `concept`
- `quiz_item`

It also detects explicit user words such as "definition", "concept", and "quiz" and adds matching artifact types even if the router omitted them.
