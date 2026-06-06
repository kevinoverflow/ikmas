from __future__ import annotations

import sqlite3

from app.domain.types import TurnRecord
from app.infrastructure.config import DB_PATH


def get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS turns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            user_id TEXT,
            user_input TEXT NOT NULL,
            intent TEXT NOT NULL,
            distance TEXT NOT NULL,
            role TEXT NOT NULL,
            state TEXT,
            confidence REAL NOT NULL,
            llm_json TEXT NOT NULL,
            system_state TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_turns_session_created
        ON turns(session_id, created_at);

        CREATE TABLE IF NOT EXISTS artefacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project TEXT,
            type TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_artefacts_project_created
        ON artefacts(project, created_at);

        CREATE TABLE IF NOT EXISTS concepts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT
        );

        CREATE TABLE IF NOT EXISTS links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            artefact_id INTEGER NOT NULL,
            ref_type TEXT NOT NULL,
            ref_id TEXT NOT NULL,
            FOREIGN KEY(artefact_id) REFERENCES artefacts(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            name TEXT,
            email TEXT,
            password_hash TEXT,
            profile_json TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS auth_sessions (
            token_hash TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            expires_at TEXT NOT NULL,
            last_used_at TEXT,
            revoked_at TEXT,
            FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_auth_sessions_user
        ON auth_sessions(user_id, expires_at);

        CREATE TABLE IF NOT EXISTS user_knowledge (
            user_id TEXT NOT NULL,
            concept_id INTEGER NOT NULL,
            mastery REAL NOT NULL CHECK (mastery >= 0.0 AND mastery <= 1.0),
            next_review TEXT,
            PRIMARY KEY (user_id, concept_id),
            FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE,
            FOREIGN KEY(concept_id) REFERENCES concepts(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_user_knowledge
        ON user_knowledge(user_id, concept_id);

        -- NEW TABLE for session history
        CREATE TABLE IF NOT EXISTS session_history (
            session_id TEXT PRIMARY KEY,
            user_id TEXT,
            session_title TEXT,
            timestamp DATETIME,
            router_classification JSON,
            user_query TEXT,
            generated_artefacts JSON,
            citations_used JSON,
            user_feedback JSON,
            session_embedding BLOB
        );

        -- Indexes for fast queries
        CREATE INDEX IF NOT EXISTS idx_sessions_user_time ON session_history(user_id, timestamp);
        CREATE INDEX IF NOT EXISTS idx_sessions_class ON session_history(router_classification);
        """)

        _ensure_column(conn, "users", "name", "TEXT")
        _ensure_column(conn, "users", "email", "TEXT")
        _ensure_column(conn, "users", "password_hash", "TEXT")
        _ensure_column(conn, "users", "created_at", "TEXT DEFAULT CURRENT_TIMESTAMP")
        _ensure_column(conn, "session_history", "session_title", "TEXT")
        _ensure_column(conn, "auth_sessions", "last_used_at", "TEXT")
        _ensure_column(conn, "auth_sessions", "revoked_at", "TEXT")
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email)")


def _ensure_column(
    conn: sqlite3.Connection,
    table: str,
    column: str,
    definition: str,
) -> None:
    columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def create_session(session_id: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO sessions(session_id) VALUES (?)",
            (session_id,),
        )


def log_turn(turn: TurnRecord) -> None:
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO turns(
                session_id, user_id, user_input, intent, distance, role, state,
                confidence, llm_json, system_state
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            turn.session_id,
            turn.user_id,
            turn.user_input,
            turn.intent,
            turn.distance,
            turn.role,
            turn.state,
            turn.confidence,
            turn.llm_json,
            turn.system_state,
        ))


def save_artefacts(artefacts: list[dict], project: str, refs: list[dict]) -> list[int]:
    ids: list[int] = []

    with get_conn() as conn:
        for artefact in artefacts:
            cur = conn.execute("""
                INSERT INTO artefacts(project, type, title, content)
                VALUES (?, ?, ?, ?)
            """, (
                project,
                artefact["type"],
                artefact["title"],
                artefact["content"],
            ))

            artefact_id = cur.lastrowid
            ids.append(artefact_id)

            for ref in refs:
                conn.execute("""
                    INSERT INTO links(artefact_id, ref_type, ref_id)
                    VALUES (?, ?, ?)
                """, (
                    artefact_id,
                    ref.get("ref_type", "citation"),
                    ref.get("ref_id", ""),
                ))

    return ids


def upsert_user_knowledge(
    user_id: str,
    concept_id: int,
    mastery: float,
    next_review: str | None,
) -> None:
    mastery = max(0.0, min(1.0, mastery))

    with get_conn() as conn:
        conn.execute("""
            INSERT INTO user_knowledge(user_id, concept_id, mastery, next_review)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, concept_id)
            DO UPDATE SET mastery = excluded.mastery,
                          next_review = excluded.next_review
        """, (user_id, concept_id, mastery, next_review))

def store_session_history(
    session_id: str,
    user_id: str,
    user_input: str,
    router_classification: dict,
    generated_artefacts: list[str],
    citations_used: list[str],
    db_provider
) -> None:
    """Store session history for future routing and context."""
    import json
    
    with get_conn() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO session_history(
                session_id, user_id, session_title, timestamp, 
                router_classification, user_query, generated_artefacts, 
                citations_used, user_feedback, session_embedding
            ) VALUES (?, ?, ?, datetime('now'), ?, ?, ?, ?, ?, ?)
        """, (
            session_id,
            user_id,
            f"Session {session_id}",
            json.dumps(router_classification),
            user_input,
            json.dumps(generated_artefacts),
            json.dumps(citations_used),
            json.dumps({}),  # Empty feedback initially
            None  # No embedding initially
        ))
