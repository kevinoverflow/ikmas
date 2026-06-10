# Roles

IKMAS is based on a planned SECI x Markus role matrix, but only four role prompts are active in the current runtime.

## Active Roles

Active roles must be present in all of these places:

- `RoleName` in `app/domain/types.py`
- `RouterPayload.selected_agent` in `app/domain/schema.py`
- `AGENT_REGISTRY` and aliases in `app/backend/router_agent.py`
- prompt registration in `app/prompts/prompts.py`

Current active set:

| Role | Prompt | SECI / reuse situation used by router |
|---|---|---|
| `ScribeAgent` | `app/prompts/scribe_agent.py` | Externalization / Shared Work Producer |
| `SemanticLinkingAgent` | `app/prompts/semantic_linking_agent.py` | Combination / Shared Work Producer |
| `MentorAgent` | `app/prompts/mentor_agent.py` | Socialization or Internalization / Expertise-Seeking Novice |
| `ContextReconstructorAgent` | `app/prompts/context_reconstructor_agent.py` | Combination or Internalization / Secondary Knowledge Miner |

## Role Responsibilities

### ScribeAgent

Transforms fragmented work traces into structured reusable documentation. The prompt emphasizes not inventing missing information and labeling interpretation.

### SemanticLinkingAgent

Identifies conceptual relationships, redundancies, contradictions, missing links, and suggested tags across explicit artifacts.

### MentorAgent

Explains expert knowledge for a novice audience with accessible language, examples, misunderstandings, reflection questions, and appropriate uncertainty boundaries.

### ContextReconstructorAgent

Reconstructs background context, assumptions, applicability conditions, transfer risks, and validation questions for artifacts reused outside their original context.

## Planned Matrix

The broader research design describes a 4 x 4 matrix of SECI modes and Markus reuse situations. Most cells are not implemented as runtime agents.

| SECI / Markus | Shared Work Producer | Shared Work Practitioner | Expertise-Seeking Novice | Secondary Knowledge Miner |
|---|---|---|---|---|
| Socialization | Planned | Planned | `MentorAgent` | Planned |
| Externalization | `ScribeAgent` | Planned | Planned | Planned |
| Combination | `SemanticLinkingAgent` | Planned | Planned | `ContextReconstructorAgent` |
| Internalization | Planned | Planned | `MentorAgent` | `ContextReconstructorAgent` |

## Not Active

These names may appear in older design notes, but they are not active roles in the current application:

- Digital Memory Agent
- Expert Proxy Agent
- Synthetic Expert Agent
- Context Elicitation Agent
- Problem Formulation Agent
- Cross-Context Reframing Agent
- Synthesis Linker Agent
- Adaptive Curator Agent
- Concept Mining Agent
- Personal Context Restoration Agent
- Experience Simulation Agent
- Tutoring Agent
- Ideation Trigger Agent
- Silent Scribe
- Knowledge Interviewer
- Curator/Synthesizer
- Simulation Agent

Do not document them as implemented unless code paths, schema support, prompt registration, and tests are added.
