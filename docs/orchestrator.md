# Orchestrator

`app/backend/orchestrator.py` is the central runtime module. Its primary entry point is:

```python
handle_turn(
    *,
    session_id: str,
    user_input: str,
    user_id: str | None = None,
    collection_name: str | None = None,
    chat_history: list[dict[str, str]] | None = None,
    model_override: str | None = None,
) -> dict[str, Any]
```

`orchestrate(...)` is a compatibility wrapper that delegates to `handle_turn(...)`.

## Pipeline

1. `init_db()` ensures SQLite tables and migrations exist.
2. `create_session(session_id)` inserts the session if it does not exist.
3. `_collection_for_user(...)` resolves the active collection.
4. `route_with_agent(...)` classifies the request and returns `RouteDecision`.
5. `run_retrieval(...)` retrieves and reranks chunks from Chroma.
6. `decide_state(...)` computes an optional tutor state. Normal active roles usually produce `None`.
7. `model_selection_for_role(...)` chooses the answer model unless the UI supplied `model_override`.
8. `build_prompt(...)` constructs the JSON-only role prompt.
9. `LLMClient.generate_json(...)` calls the LLM and enforces the assistant schema.
10. `normalize_artifact_generation_plan(...)` finalizes artifact requests.
11. `artifact_reuse_agent.find_reusable_artifacts(...)` reuses saved artifacts where possible.
12. `_generate_subagent_artefacts(...)` creates missing artifacts through the coordinator.
13. `AssistantPayload.model_validate(...)` validates the final payload including router debug data.
14. `log_turn(...)` stores the full turn.
15. `store_session_history(...)` upserts the latest session summary.
16. `save_artefacts(...)` persists newly generated artifacts and source chunk links.

## Prompt Inputs

`build_prompt(...)` includes:

- role instructions from `app/prompts/prompts.py`
- selected role and state
- router reason, distance, knowledge mode, confidence
- session context: detected themes, knowledge gaps, related sessions
- last six chat turns
- retrieved chunks with source, page, chunk id, and text
- user request
- required JSON response shape

## Output

The return value is a validated `AssistantPayload` dict:

- `assistant_message`
- `questions`
- `artefacts`
- `actions`
- `citations`
- `telemetry`
- `router_debug`

The Streamlit UI renders this payload directly.
