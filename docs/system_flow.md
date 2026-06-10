# System Flow

## Chat Turn Flow

```text
Streamlit chat input
  -> app.ui.chat._ask_assistant(...)
  -> app.backend.orchestrator.handle_turn(...)
  -> init_db() + create_session()
  -> route_with_agent(...)
  -> run_retrieval(...)
  -> decide_state(...)
  -> build_prompt(...)
  -> LLMClient.generate_json(...)
  -> artifact reuse
  -> artifact subagent generation
  -> AssistantPayload validation
  -> citation merge
  -> log_turn(...)
  -> store_session_history(...)
  -> save_artefacts(...)
  -> payload returned to UI
```

## File Indexing Flow

```text
File uploader
  -> save_upload(...)
  -> data/uploads/<collection_id>/
  -> Index now button
  -> split_file(...)
  -> split_documents(...)
  -> add_docs(...)
  -> Chroma collection
```

## Artifact Flow

```text
Router artifact_generation_plan
  -> reuse saved artifacts where possible
  -> generate missing definition/concept/quiz_item artifacts
  -> include artifacts in AssistantPayload
  -> persist new artifacts
  -> render in artifact browser
```

## Session History Flow

Each turn logs full payload data to `turns`. Each session also maintains one summary row in `session_history`. The router reads recent session-history rows for authenticated users and injects recurring route themes plus related sessions into the router prompt.

Current limitation: session embeddings are stored as a nullable placeholder, and knowledge-gap extraction is not implemented.
