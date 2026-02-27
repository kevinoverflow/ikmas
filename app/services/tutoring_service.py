from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict

from app.services.contracts import TutoringServiceContract
from app.services.user_model_service import UserModelService


class TutoringService(TutoringServiceContract):
    def __init__(self, user_model_service: UserModelService):
        self.user_model_service = user_model_service

    def run_assessment(self, user_id: str, topic: str, score: float, confidence: float) -> Dict[str, object]:
        bounded_score = min(max(score, 0.0), 1.0)
        bounded_conf = min(max(confidence, 0.0), 1.0)

        self.user_model_service.update_assessment(
            user_id=user_id,
            topic=topic,
            score=bounded_score,
            confidence=bounded_conf,
        )

        # Simple spaced-repetition seed interval.
        days = 1 if bounded_score < 0.5 else 3 if bounded_score < 0.8 else 7
        due_at = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()
        self.user_model_service.schedule_review(user_id, due_at, f"Auto-scheduled after assessment for topic={topic}")

        return {
            "user_id": user_id,
            "topic": topic,
            "score": bounded_score,
            "confidence": bounded_conf,
            "next_review_at": due_at,
        }

    def run_practice(self, user_id: str, prompt: str, quality_score: float) -> Dict[str, object]:
        bounded = min(max(quality_score, 0.0), 1.0)
        # Practice updates global assessment lightly.
        self.user_model_service.update_assessment(
            user_id=user_id,
            topic="global",
            score=bounded,
            confidence=0.6,
        )
        return {
            "user_id": user_id,
            "prompt": prompt,
            "quality_score": bounded,
            "feedback": "Practice recorded. Continue with teach-back and a follow-up scenario.",
        }
