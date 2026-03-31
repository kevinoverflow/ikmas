# Sqlite Store

## Overview

`sqlite_store.py` is the persistence layer for the orchestration backend.

It manages:

- session creation
- turn logging
- artefact storage
- citation/reference linking
- user knowledge tracking

The module uses SQLite as the operational knowledge layer.

---

## Responsibilities

This module provides a minimal storage API for:

- initializing the database schema
- creating sessions
- persisting validated turn payloads
- storing generated artefacts
- updating user mastery over concepts

It is intentionally simple and deterministic.

---

## Database Connection

### `get_conn()`

Creates a SQLite connection with:

- `sqlite3.Row` row factory
- foreign key enforcement enabled
- automatic database directory creation

```python
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
conn.execute("PRAGMA foreign_keys = ON;")
```
