from __future__ import annotations

import json
from typing import Any

from app.domain.schema import AssistantPayload


class LLMClient:
    """
    Backend-facing LLM client with strict JSON handling.

    Responsibility:
    - call the provider backend
    - validate schema
    - perform one repair attempt
    - return deterministic fallback if repair fails
    """

    def __init__(self, backend):
        self.backend = backend

    def generate_json(
        self,
        prompt: str,
        *,
        fallback_role: str = "MentorAgent",
        fallback_state: str | None = None,
        fallback_intent: str = "what_is",
        fallback_distance: str = "ESN",
        fallback_confidence: float = 0.0,
        fallback_retrieval_count: int = 0,
    ) -> dict[str, Any]:
        raw = self.backend.generate(
            prompt,
            system_prompt=(
                "You are a precise assistant. "
                "Return only valid JSON. "
                "Do not use markdown fences. "
                "Do not include explanations outside the JSON."
            ),
            temperature=0.2,
        )

        try:
            data = self.parse_and_validate_json(raw)
            data["telemetry"]["repair_used"] = False
            data["telemetry"]["fallback_used"] = False
            return data
        except Exception:
            repaired = self.repair_json(raw)
            if repaired is not None:
                return repaired

            return self.fallback_payload(
                role=fallback_role,
                state=fallback_state,
                intent=fallback_intent,
                distance=fallback_distance,
                confidence=fallback_confidence,
                retrieval_count=fallback_retrieval_count,
            )

    def repair_json(self, bad_output: str) -> dict[str, Any] | None:
        repair_prompt = (
            "Repair the following model output into valid JSON matching the required schema.\n"
            "Return JSON only.\n"
            "Do not add markdown fences.\n"
            "Do not add explanations.\n\n"
            f"ORIGINAL OUTPUT:\n{bad_output}"
        )

        raw = self.backend.generate(
            repair_prompt,
            system_prompt=(
                "You repair malformed outputs into valid JSON. "
                "Return only corrected JSON."
            ),
            temperature=0.0,
        )

        try:
            data = self.parse_and_validate_json(raw)
            data["telemetry"]["repair_used"] = True
            data["telemetry"]["fallback_used"] = False
            return data
        except Exception:
            return None

    @staticmethod
    def parse_and_validate_json(raw: str) -> dict[str, Any]:
        """
        Parse raw model output as JSON and validate it against AssistantPayload.
        """
        parsed = json.loads(raw)
        payload = AssistantPayload.model_validate(parsed)
        return payload.model_dump()

    @staticmethod
    def fallback_payload(
        *,
        role: str,
        state: str | None,
        intent: str,
        distance: str,
        confidence: float,
        retrieval_count: int,
    ) -> dict[str, Any]:
        """
        Deterministic schema-valid fallback payload.
        """
        payload = {
            "role": role,
            "state": state,
            "assistant_message": (
                "I could not produce a fully reliable structured answer yet. "
                "Please clarify your request briefly so I can continue."
            ),
            "questions": [
                {
                    "id": "clarify_topic",
                    "type": "text",
                    "label": "What exact topic, concept, or document should I focus on?",
                    "options": [],
                    "required": True,
                },
                {
                    "id": "clarify_goal",
                    "type": "single_choice",
                    "label": "What do you want next?",
                    "options": [
                        "Simple explanation",
                        "Project-specific answer",
                        "Practice questions",
                        "Summary",
                    ],
                    "required": True,
                },
            ],
            "artefacts": [],
            "actions": [
                {
                    "type": "ask",
                    "payload": {},
                }
            ],
            "citations": [],
            "telemetry": {
                "intent": intent,
                "distance": distance,
                "confidence": confidence,
                "retrieval_count": retrieval_count,
                "repair_used": False,
                "fallback_used": True,
            },
        }

        validated = AssistantPayload.model_validate(payload)
        return validated.model_dump()