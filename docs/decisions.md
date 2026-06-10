# Design Decisions

## Use Streamlit as the Runtime Shell

The application is implemented as a Streamlit app rather than a separate web frontend/backend pair. This keeps auth, uploads, indexing controls, chat, citations, and artifacts in one Python runtime.

## Scope Workspaces by User

Authenticated users are mapped to user-specific collection ids. This keeps uploaded files, Chroma collections, and saved artifacts separate without requiring a multi-tenant service layer.

## Route Before Retrieval

The orchestrator routes first, then retrieves. Routing provides role instructions, model selection, debug metadata, and artifact-generation intent. Retrieval then supplies source context for the selected role.

## Use Strict JSON for Assistant Output

The UI expects structured payloads. `AssistantPayload` makes responses renderable, persistable, and testable. `LLMClient` normalizes, repairs, salvages, or falls back to preserve this contract.

## Store Source Chunks and Artifacts Separately

Chroma stores source-document chunks for retrieval. SQLite stores generated artifacts and links them to source chunks. This lets artifacts be edited, deleted, regenerated, and reused independently of vector storage.

## Keep the FSM Dormant Until Tutor Is Real

`fsm.py` contains tutor-state logic, but the active role schema does not include `TutoringAgent`. The current design avoids pretending that the full tutor loop exists before routing, UI actions, user-model updates, and scheduling are implemented.

## Prefer Native File Workspace Controls

The file workspace uses native Streamlit widgets and backend storage helpers rather than a third-party file browser. This keeps dedupe, conflict handling, downloads, deletes, and indexing explicit in the codebase.
