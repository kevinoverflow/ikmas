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
            profile_json TEXT
        );

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
        """)


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