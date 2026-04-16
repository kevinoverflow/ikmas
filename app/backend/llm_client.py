from __future__ import annotations

import json
from json import JSONDecodeError
from typing import Any

from app.domain.schema import AssistantPayload
from app.infrastructure.tracing import traceable
from app.rag.llm import OpenAIChatBackend


def get_client():
    """
    Compatibility helper for UI code that needs raw access to the provider client.
    """
    return OpenAIChatBackend().client


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

    @traceable(name="generate_structured_response", run_type="chain")
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
            response_format={"type": "json_object"},
        )

        try:
            data = self.parse_and_validate_json(
                raw,
                role=fallback_role,
                state=fallback_state,
                intent=fallback_intent,
                distance=fallback_distance,
                confidence=fallback_confidence,
                retrieval_count=fallback_retrieval_count,
            )
            data["telemetry"]["repair_used"] = False
            data["telemetry"]["fallback_used"] = False
            return data
        except Exception:
            repaired = self.repair_json(raw)
            if repaired is not None:
                return repaired

            salvaged = self.salvage_payload(
                raw,
                role=fallback_role,
                state=fallback_state,
                intent=fallback_intent,
                distance=fallback_distance,
                confidence=fallback_confidence,
                retrieval_count=fallback_retrieval_count,
            )
            if salvaged is not None:
                return salvaged

            return self.fallback_payload(
                role=fallback_role,
                state=fallback_state,
                intent=fallback_intent,
                distance=fallback_distance,
                confidence=fallback_confidence,
                retrieval_count=fallback_retrieval_count,
            )

    @traceable(name="repair_structured_response", run_type="chain")
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
            response_format={"type": "json_object"},
        )

        try:
            data = self.parse_and_validate_json(
                raw,
                role="MentorAgent",
                state=None,
                intent="what_is",
                distance="ESN",
                confidence=0.0,
                retrieval_count=0,
            )
            data["telemetry"]["repair_used"] = True
            data["telemetry"]["fallback_used"] = False
            return data
        except Exception:
            return None

    @staticmethod
    def parse_and_validate_json(
        raw: str,
        *,
        role: str,
        state: str | None,
        intent: str,
        distance: str,
        confidence: float,
        retrieval_count: int,
    ) -> dict[str, Any]:
        """
        Parse raw model output as JSON and validate it against AssistantPayload.
        """
        parsed = LLMClient._load_json_object(raw)
        normalized = LLMClient._normalize_payload(
            parsed,
            role=role,
            state=state,
            intent=intent,
            distance=distance,
            confidence=confidence,
            retrieval_count=retrieval_count,
        )
        payload = AssistantPayload.model_validate(normalized)
        return payload.model_dump()

    @staticmethod
    def _load_json_object(raw: str) -> dict[str, Any]:
        text = raw.strip()
        candidates = [text]

        if "```" in text:
            stripped = text.replace("```json", "```").replace("```JSON", "```")
            fence_parts = stripped.split("```")
            candidates.extend(part.strip() for part in fence_parts if part.strip())

        first = text.find("{")
        last = text.rfind("}")
        if first != -1 and last != -1 and first < last:
            candidates.append(text[first:last + 1].strip())

        for candidate in candidates:
            try:
                parsed = json.loads(candidate)
            except JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                return parsed

        raise JSONDecodeError("No JSON object found in model output.", text, 0)

    @staticmethod
    def _normalize_payload(
        parsed: dict[str, Any],
        *,
        role: str,
        state: str | None,
        intent: str,
        distance: str,
        confidence: float,
        retrieval_count: int,
    ) -> dict[str, Any]:
        valid_roles = {
            "DigitalMemoryAgent",
            "MentorAgent",
            "TutoringAgent",
            "ConceptMiningAgent",
        }
        valid_states = {"ASSESS", "EXPLAIN", "CHECK", "PRACTICE", "FEEDBACK", "SCHEDULE"}
        valid_question_types = {"single_choice", "multi_choice", "text"}
        valid_artefact_types = {"summary", "flashcards", "quiz", "checklist", "note", "concept_map"}
        valid_action_types = {"ask", "store_artefact", "schedule_review", "update_mastery", "none"}

        normalized_role = parsed.get("role")
        if normalized_role not in valid_roles:
            normalized_role = role

        normalized_state = parsed.get("state")
        if normalized_state not in valid_states:
            normalized_state = state if state in valid_states else None

        assistant_message = ""
        for key in ("assistant_message", "message", "answer", "response", "content"):
            value = parsed.get(key)
            if isinstance(value, str) and value.strip():
                assistant_message = value.strip()
                break

        normalized_questions: list[dict[str, Any]] = []
        for idx, question in enumerate(parsed.get("questions", []), start=1):
            if not isinstance(question, dict):
                continue
            q_type = question.get("type")
            if q_type not in valid_question_types:
                q_type = "text"
            label = question.get("label") or question.get("question") or question.get("prompt")
            if not isinstance(label, str) or not label.strip():
                continue
            options = question.get("options")
            if not isinstance(options, list):
                options = []
            normalized_questions.append(
                {
                    "id": str(question.get("id") or f"q{idx}"),
                    "type": q_type,
                    "label": label.strip(),
                    "options": [str(option) for option in options if isinstance(option, (str, int, float))],
                    "required": bool(question.get("required", True)),
                }
            )

        normalized_artefacts: list[dict[str, Any]] = []
        for artefact in parsed.get("artefacts", []):
            if not isinstance(artefact, dict):
                continue
            artefact_type = artefact.get("type")
            title = artefact.get("title")
            content = artefact.get("content")
            if artefact_type not in valid_artefact_types:
                continue
            if not isinstance(title, str) or not title.strip():
                continue
            if not isinstance(content, str) or not content.strip():
                continue
            concept_ids = artefact.get("concept_ids")
            if not isinstance(concept_ids, list):
                concept_ids = []
            normalized_artefacts.append(
                {
                    "type": artefact_type,
                    "title": title.strip(),
                    "content": content.strip(),
                    "concept_ids": [int(value) for value in concept_ids if isinstance(value, int)],
                }
            )

        normalized_actions: list[dict[str, Any]] = []
        for action in parsed.get("actions", []):
            if not isinstance(action, dict):
                continue
            action_type = action.get("type")
            if action_type not in valid_action_types:
                continue
            payload = action.get("payload")
            normalized_actions.append(
                {
                    "type": action_type,
                    "payload": payload if isinstance(payload, dict) else {},
                }
            )
        if not normalized_actions:
            normalized_actions = [{"type": "none", "payload": {}}]

        normalized_citations: list[dict[str, Any]] = []
        for citation in parsed.get("citations", []):
            if not isinstance(citation, dict):
                continue
            source = citation.get("source")
            chunk_id = citation.get("chunk_id")
            if not isinstance(source, str) or not source.strip():
                continue
            if not isinstance(chunk_id, str) or not chunk_id.strip():
                continue
            title = citation.get("title")
            locator = citation.get("locator")
            normalized_citations.append(
                {
                    "source": source.strip(),
                    "chunk_id": chunk_id.strip(),
                    "title": title.strip() if isinstance(title, str) and title.strip() else None,
                    "locator": locator.strip() if isinstance(locator, str) and locator.strip() else None,
                }
            )

        telemetry = parsed.get("telemetry")
        if not isinstance(telemetry, dict):
            telemetry = {}

        return {
            "role": normalized_role,
            "state": normalized_state,
            "assistant_message": assistant_message,
            "questions": normalized_questions,
            "artefacts": normalized_artefacts,
            "actions": normalized_actions,
            "citations": normalized_citations,
            "telemetry": {
                "intent": str(telemetry.get("intent") or intent),
                "distance": str(telemetry.get("distance") or distance),
                "confidence": float(telemetry.get("confidence", confidence)),
                "retrieval_count": int(telemetry.get("retrieval_count", retrieval_count)),
                "repair_used": bool(telemetry.get("repair_used", False)),
                "fallback_used": bool(telemetry.get("fallback_used", False)),
            },
        }

    @staticmethod
    def salvage_payload(
        raw: str,
        *,
        role: str,
        state: str | None,
        intent: str,
        distance: str,
        confidence: float,
        retrieval_count: int,
    ) -> dict[str, Any] | None:
        text = raw.strip()
        if not text:
            return None

        payload = {
            "role": role,
            "state": state,
            "assistant_message": text,
            "questions": [],
            "artefacts": [],
            "actions": [{"type": "none", "payload": {}}],
            "citations": [],
            "telemetry": {
                "intent": intent,
                "distance": distance,
                "confidence": confidence,
                "retrieval_count": retrieval_count,
                "repair_used": True,
                "fallback_used": False,
            },
        }
        validated = AssistantPayload.model_validate(payload)
        return validated.model_dump()

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
