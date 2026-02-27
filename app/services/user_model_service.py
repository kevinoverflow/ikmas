from __future__ import annotations

from typing import Dict, List

from app.domain.types import UserModelSnapshot
from app.infrastructure.db import db_cursor
from app.services.contracts import UserModelServiceContract


class UserModelService(UserModelServiceContract):
    def _ensure_user(self, user_id: str) -> None:
        with db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO user_profile (user_id)
                VALUES (?)
                ON CONFLICT(user_id) DO NOTHING
                """,
                (user_id,),
            )

    def get_snapshot(self, user_id: str) -> UserModelSnapshot:
        self._ensure_user(user_id)
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT distance, confidence
                FROM knowledge_distance
                WHERE user_id = ? AND topic = 'global'
                """,
                (user_id,),
            )
            kd = cur.fetchone()
            cur.execute(
                """
                SELECT due_at
                FROM review_schedule
                WHERE user_id = ? AND status = 'pending'
                ORDER BY due_at ASC
                LIMIT 1
                """,
                (user_id,),
            )
            nxt = cur.fetchone()
            cur.execute(
                """
                SELECT goal
                FROM learning_goals
                WHERE user_id = ? AND active = 1
                ORDER BY id DESC
                LIMIT 1
                """,
                (user_id,),
            )
            goal = cur.fetchone()
            cur.execute(
                """
                SELECT AVG(score) AS avg_score
                FROM progress
                WHERE user_id = ?
                """,
                (user_id,),
            )
            prog = cur.fetchone()

        avg = float(prog["avg_score"]) if prog and prog["avg_score"] is not None else 0.0
        progress = min(max(avg, 0.0), 1.0)
        distance = float(kd["distance"]) if kd else 0.5
        return UserModelSnapshot(
            user_id=user_id,
            knowledge_distance=distance,
            learning_progress=progress,
            goal=goal["goal"] if goal else None,
            next_review_at=nxt["due_at"] if nxt else None,
        )

    def update_assessment(self, user_id: str, topic: str, score: float, confidence: float) -> None:
        self._ensure_user(user_id)
        distance = 1.0 - min(max(score, 0.0), 1.0)
        with db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO knowledge_distance (user_id, topic, distance, confidence)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, topic)
                DO UPDATE SET
                    distance = excluded.distance,
                    confidence = excluded.confidence,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (user_id, topic, distance, confidence),
            )
            cur.execute(
                """
                INSERT INTO progress (user_id, state, score, confidence, evidence)
                VALUES (?, 'assess', ?, ?, ?)
                """,
                (user_id, score, confidence, f"Assessment topic={topic}"),
            )

    def schedule_review(self, user_id: str, due_at: str, reason: str) -> None:
        self._ensure_user(user_id)
        with db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO review_schedule (user_id, due_at, reason)
                VALUES (?, ?, ?)
                """,
                (user_id, due_at, reason),
            )

    def get_schedule(self, user_id: str) -> List[Dict[str, str]]:
        self._ensure_user(user_id)
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT id, due_at, status, reason, created_at, updated_at
                FROM review_schedule
                WHERE user_id = ?
                ORDER BY due_at ASC
                """,
                (user_id,),
            )
            rows = cur.fetchall()
        return [dict(r) for r in rows]
