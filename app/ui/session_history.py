from __future__ import annotations

import json
from dataclasses import dataclass

from app.backend.sqlite_store import get_conn


@dataclass(frozen=True)
class ChatSessionSummary:
    session_id: str
    title: str | None
    user_query: str | None
    timestamp: str | None

    @property
    def display_title(self) -> str:
        return self.title or self.user_query or "Untitled chat"


def load_session_chat_history(session_id: str, user_id: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT user_input, llm_json
            FROM turns
            WHERE session_id = ? AND user_id = ?
            ORDER BY created_at, id
            """,
            (session_id, user_id),
        ).fetchall()

    history = []
    for row in rows:
        try:
            payload = json.loads(row["llm_json"])
        except (TypeError, json.JSONDecodeError):
            continue
        history.append({"user": row["user_input"], "payload": payload})
    return history


def list_recent_chat_sessions(user_id: str, *, limit: int = 20) -> list[ChatSessionSummary]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT session_id, session_title, user_query, timestamp
            FROM session_history
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()

    return [
        ChatSessionSummary(
            session_id=row["session_id"],
            title=row["session_title"],
            user_query=row["user_query"],
            timestamp=row["timestamp"],
        )
        for row in rows
    ]
