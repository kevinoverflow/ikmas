# SQLite Persistence

SQLite is the operational persistence layer. The database path is `data/ikmas.db`.

`app/backend/sqlite_store.py` owns connection setup, schema initialization, migrations for added columns, and storage helpers.

## Connection

`get_conn()`:

- creates the parent directory,
- opens `DB_PATH`,
- sets `sqlite3.Row`,
- enables foreign keys.

## Tables

| Table | Purpose |
|---|---|
| `sessions` | Chat session ids and creation timestamps |
| `turns` | Full turn log: user input, role, state, route fields, confidence, payload JSON, system state |
| `artefacts` | Persisted generated artifacts scoped by project/collection |
| `links` | References from artifacts to source chunks or other refs |
| `concepts` | Named concept records |
| `user_knowledge` | User/concept mastery and next-review placeholder |
| `users` | Auth profile, email, password hash, profile JSON |
| `auth_sessions` | Remember-me token hashes, expiry, last use, revocation |
| `session_history` | One-row session summaries for router context and UI history |

## Main APIs

- `init_db()`
- `create_session(session_id)`
- `log_turn(turn)`
- `save_artefacts(artefacts, project, refs)`
- `list_artefacts(project, limit=100)`
- `get_artefact(artefact_id)`
- `update_artefact(...)`
- `delete_artefact(...)`
- `find_similar_artefacts(...)`

Authentication APIs live in `app/backend/auth.py` but use the same database.

## Session History

`store_session_history(...)` in `orchestrator.py` writes:

- session title
- latest user query
- router classification JSON
- generated artifact titles
- citation chunk IDs
- feedback JSON placeholder
- nullable session embedding

The router reads recent rows for the current user to provide related-session context. Semantic session embeddings are not implemented.
