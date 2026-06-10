# Intent and Distance

This repository contains two classification paths:

1. The active LLM router in `app/backend/router_agent.py`.
2. Legacy/deterministic helpers in `app/backend/intent_distance.py` and `app/backend/role_router.py`.

The active orchestrator path uses the LLM router.

## Active Router Labels

The router classifies:

- SECI mode: `Socialization`, `Externalization`, `Combination`, `Internalization`
- Markus reuse situation: `Shared Work Producer`, `Shared Work Practitioner`, `Expertise-Seeking Novice`, `Secondary Knowledge Miner`
- selected active role

The router then maps reuse situations to compact internal distance labels:

| Reuse situation | Distance |
|---|---|
| Shared Work Producer | `SWP` |
| Shared Work Practitioner | `SWPr` |
| Expertise-Seeking Novice | `ESN` |
| Secondary Knowledge Miner | `SKM` |

SECI modes are mapped to internal knowledge modes:

| SECI mode | KnowledgeMode |
|---|---|
| Socialization | `SOCIALIZATION` |
| Externalization | `EXTERNALIZATION` |
| Combination | `COMBINATION` |
| Internalization | `INTERNALIZATION` |

## Legacy Helpers

`app/backend/intent_distance.py` provides keyword/rule-based intent and distance scoring used by tests and earlier iterations. `app/backend/role_router.py` maps a small subset of `(Distance, KnowledgeMode)` pairs to active roles and falls back to `MentorAgent`.

These helpers are useful for deterministic tests and future fallback design, but they are not the primary routing mechanism in `handle_turn(...)`.

## Current Practical Meaning

In persisted turns, `intent` is currently the router's free-text `reason`, not a closed intent enum. `distance` is the compact Markus label returned by the active route normalization.
