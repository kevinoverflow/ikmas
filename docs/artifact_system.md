# Artifact System

The artifact system turns explicit user requests for learning objects into reusable saved artifacts. It runs after the main assistant response has been generated, so artifacts can combine user intent, retrieved source chunks, existing saved artifacts, and the answer context.

## Implemented Artifact Types

Only these types are executable end-to-end today:

| Type | Generator | Output |
|---|---|---|
| `definition` | `DefinitionGeneratorAgent` | One or more formal definitions with scope notes |
| `concept` | `ConceptMapperAgent` | Concept explanation cards with relationships and examples |
| `quiz_item` | `QuizGeneratorAgent` | Multiple-choice quiz items with explanation and evidence reference |

`ArtifactType` also lists `prerequisite`, `pitfall`, and `case`, but those are placeholders until generators and UI behavior are added.

## Runtime Flow

```text
RouterPayload.artifact_generation_plan
  -> normalize_artifact_generation_plan(...)
  -> _desired_artifact_counts(...)
  -> ArtifactReuseAgent.find_reusable_artifacts(...)
  -> SubagentCoordinator.spawn_subagent(...)
  -> concrete generator .generate(...)
  -> ArtifactResult
  -> orchestrator conversion helpers
  -> AssistantPayload.artefacts
  -> save_artefacts(...)
  -> artifact browser
```

The router may request artifacts through its JSON plan, and explicit user words such as "definition", "concept", or "quiz" are also detected heuristically.

## Reuse

`ArtifactReuseAgent` searches saved SQLite artifacts by project/collection and type. It uses `find_similar_artefacts(...)` plus a string-similarity threshold to decide whether a saved artifact can satisfy the current request. If enough reusable artifacts exist, generation is skipped for that type. If fewer than the desired count exist, the type remains in the missing list and is generated.

## Generation

`SubagentCoordinator` keeps a small in-memory registry of generator factories:

- `definition` -> `DefinitionGeneratorAgent`
- `concept` -> `ConceptMapperAgent`
- `quiz_item` -> `QuizGeneratorAgent`

Each generator receives an `ArtifactGenerationContext` containing:

- original user input
- source context from retrieved chunks or the user input
- related artifacts
- target audience
- session id

The generator calls the same OpenAI-compatible backend used by the answer model and returns an `ArtifactResult`.

## Persistence and UI

New artifacts are saved to the `artefacts` table with the collection id in the `project` column. The first retrieved chunks are stored as `links` with `ref_type="chunk"`.

`app/ui/artifacts.py` merges persisted artifacts with artifacts from the current unsaved chat history, filters by type, renders quiz items interactively, and exposes management actions for persisted artifacts:

- edit title/content
- delete
- regenerate

Regeneration tries the type-specific generator for `definition`, `concept`, and `quiz_item`. Other artifact types fall back to a generic LLM rewrite prompt.
