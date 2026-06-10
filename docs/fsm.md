# FSM

`app/backend/fsm.py` currently implements only a tutor-state helper. It is not a full S0-S7 orchestration state machine.

## Active Behavior

```python
decide_state(
    role: str,
    retrieval_confidence: float,
    session_ctx: dict,
    force_tutor_mode: bool = False,
) -> str | None
```

If `role != "TutoringAgent"` and `force_tutor_mode` is false, the function returns `None`.

Because `TutoringAgent` is not an active `RoleName` and is not emitted by the current router schema, normal application turns usually have:

```python
state = None
```

## Tutor States

When forced or called with `role == "TutoringAgent"`, the helper cycles:

```text
ASSESS -> EXPLAIN -> CHECK -> PRACTICE -> FEEDBACK -> SCHEDULE -> ASSESS
```

Initial state:

- retrieval confidence `>= 0.75`: `EXPLAIN`
- otherwise: `ASSESS`

## Session-Awareness Hooks

The function reads `detected_themes`, `knowledge_gaps`, and `related_sessions` from `session_ctx`, but the current branches are placeholders and do not change state.

## Planned

A complete Tutor Agent would need:

- registered role and prompt,
- router support,
- UI handling for teach-back/practice/schedule actions,
- user mastery updates,
- spaced repetition scheduling.
