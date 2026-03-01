from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.infrastructure.config import SQLITE_DB_PATH


@dataclass
class TurnRecord:
    session_id: str
    user_message: str
    chosen_role: str
    retrieval_confidence: float
    system_state: dict[str, Any]
    llm_json: dict[str, Any]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect() -> sqlite3.Connection:
    SQLITE_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(SQLITE_DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS artefacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                title TEXT NOT NULL,
                body_md TEXT NOT NULL,
                source_refs_json TEXT NOT NULL,
                tags_json TEXT NOT NULL,
                project TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS concepts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                definition TEXT NOT NULL,
                prerequisites_json TEXT NOT NULL,
                pitfalls_json TEXT NOT NULL,
                examples_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_type TEXT NOT NULL,
                from_id TEXT NOT NULL,
                to_type TEXT NOT NULL,
                to_id TEXT NOT NULL,
                relation TEXT NOT NULL,
                confidence REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                role TEXT NOT NULL,
                preferences_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS user_knowledge (
                user_id TEXT NOT NULL,
                concept_id INTEGER NOT NULL,
                mastery REAL NOT NULL,
                last_seen TEXT NOT NULL,
                next_review TEXT,
                PRIMARY KEY (user_id, concept_id),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (concept_id) REFERENCES concepts(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS turns (
                session_id TEXT NOT NULL,
                turn_id INTEGER NOT NULL,
                user_message TEXT NOT NULL,
                chosen_role TEXT NOT NULL,
                retrieval_confidence REAL NOT NULL,
                system_state TEXT NOT NULL,
                llm_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (session_id, turn_id),
                FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_turns_session_created ON turns(session_id, created_at);
            CREATE INDEX IF NOT EXISTS idx_artefacts_project_created ON artefacts(project, created_at);
            CREATE INDEX IF NOT EXISTS idx_user_knowledge_user_concept ON user_knowledge(user_id, concept_id);
            """
        )


def create_session(session_id: str) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO sessions(session_id, created_at) VALUES (?, ?)",
            (session_id, _utc_now()),
        )


def _next_turn_id(conn: sqlite3.Connection, session_id: str) -> int:
    row = conn.execute(
        "SELECT COALESCE(MAX(turn_id), 0) + 1 AS n FROM turns WHERE session_id = ?",
        (session_id,),
    ).fetchone()
    return int(row["n"])


def log_turn(turn: TurnRecord) -> None:
    create_session(turn.session_id)
    with _connect() as conn:
        turn_id = _next_turn_id(conn, turn.session_id)
        conn.execute(
            """
            INSERT INTO turns(
                session_id, turn_id, user_message, chosen_role, retrieval_confidence,
                system_state, llm_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                turn.session_id,
                turn_id,
                turn.user_message,
                turn.chosen_role,
                float(turn.retrieval_confidence),
                json.dumps(turn.system_state, ensure_ascii=True),
                json.dumps(turn.llm_json, ensure_ascii=True),
                _utc_now(),
            ),
        )


def get_latest_turn(session_id: str) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM turns WHERE session_id = ? ORDER BY turn_id DESC LIMIT 1",
            (session_id,),
        ).fetchone()

    if not row:
        return None

    return {
        "session_id": row["session_id"],
        "turn_id": row["turn_id"],
        "user_message": row["user_message"],
        "chosen_role": row["chosen_role"],
        "retrieval_confidence": row["retrieval_confidence"],
        "system_state": json.loads(row["system_state"]),
        "llm_json": json.loads(row["llm_json"]),
        "created_at": row["created_at"],
    }


def get_recent_turns(session_id: str, limit: int = 5) -> list[dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT user_message, llm_json FROM turns WHERE session_id = ? ORDER BY turn_id DESC LIMIT ?",
            (session_id, int(limit)),
        ).fetchall()

    out: list[dict[str, Any]] = []
    for row in reversed(rows):
        out.append({"user_message": row["user_message"], "llm_json": json.loads(row["llm_json"])})
    return out


def get_session_context(session_id: str) -> dict[str, Any]:
    last = get_latest_turn(session_id)
    if not last:
        return {}

    state = last.get("system_state", {})
    llm_json = last.get("llm_json", {})
    return {
        "last_state": llm_json.get("state"),
        "last_role": last.get("chosen_role"),
        "force_tutor_mode": bool(state.get("force_tutor_mode", False)),
        "pending_role_gate": bool(state.get("pending_role_gate", False)),
        "role_gate_questions": state.get("role_gate_questions", []),
        "role_gate_answers": state.get("role_gate_answers", {}),
    }


def save_artefacts(artefacts: list[dict], project: str, refs: list[dict]) -> list[int]:
    inserted_ids: list[int] = []
    now = _utc_now()
    with _connect() as conn:
        for art in artefacts:
            cur = conn.execute(
                """
                INSERT INTO artefacts(type, title, body_md, source_refs_json, tags_json, project, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    art.get("type", "summary"),
                    art.get("title", "Untitled"),
                    art.get("body_md", ""),
                    json.dumps(refs, ensure_ascii=True),
                    json.dumps(art.get("tags", []), ensure_ascii=True),
                    project,
                    now,
                ),
            )
            inserted_ids.append(int(cur.lastrowid))
    return inserted_ids


def save_links(from_type: str, from_id: str, to_type: str, to_id: str, relation: str, confidence: float) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO links(from_type, from_id, to_type, to_id, relation, confidence)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (from_type, from_id, to_type, to_id, relation, float(confidence)),
        )


def upsert_user(user_id: str, role: str = "member", preferences: dict | None = None) -> None:
    prefs = preferences or {}
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO users(id, role, preferences_json) VALUES (?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET role=excluded.role, preferences_json=excluded.preferences_json
            """,
            (user_id, role, json.dumps(prefs, ensure_ascii=True)),
        )


def get_user_profile(user_id: str | None) -> dict[str, Any]:
    if not user_id:
        return {"id": "anonymous", "role": "member", "preferences": {}}

    with _connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()

    if not row:
        upsert_user(user_id)
        return {"id": user_id, "role": "member", "preferences": {}}

    return {
        "id": row["id"],
        "role": row["role"],
        "preferences": json.loads(row["preferences_json"]),
    }


def upsert_user_knowledge(user_id: str, concept_id: int, mastery: float, next_review: str | None) -> None:
    now = _utc_now()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO user_knowledge(user_id, concept_id, mastery, last_seen, next_review)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id, concept_id)
            DO UPDATE SET mastery=excluded.mastery, last_seen=excluded.last_seen, next_review=excluded.next_review
            """,
            (user_id, int(concept_id), float(mastery), now, next_review),
        )


def db_path() -> Path:
    return SQLITE_DB_PATH
