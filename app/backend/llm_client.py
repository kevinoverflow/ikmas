from __future__ import annotations

import json
from typing import Any

from app.infrastructure.config import FOLLOWUP_MODEL_NAME, LANGUAGE_MODEL_NAME
from app.rag.llm import get_client
from app.backend.schema import as_schema_json


def _extract_json(text: str) -> dict[str, Any]:
    text = (text or "").strip()

    # direct JSON fast-path
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass

    # fenced code path
    if "```" in text:
        chunks = text.split("```")
        for chunk in chunks:
            chunk = chunk.strip()
            if chunk.startswith("json"):
                chunk = chunk[4:].strip()
            if not chunk:
                continue
            try:
                data = json.loads(chunk)
                if isinstance(data, dict):
                    return data
            except json.JSONDecodeError:
                continue

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        maybe = text[start : end + 1]
        data = json.loads(maybe)
        if isinstance(data, dict):
            return data

    raise ValueError("No valid JSON object found in model response")


def _build_system_prompt() -> str:
    schema = as_schema_json()
    return (
        "You are an IKMAS backend model. Output STRICT JSON only. "
        "Tone must be empathetic, concise, and supportive. "
        "Do not use markdown, prose, or extra keys. "
        "Return exactly one JSON object that matches this schema: "
        f"{schema}"
    )


def call_llm_json(
    *,
    role: str,
    state: str | None,
    user_input: str,
    intent: str,
    distance: str,
    confidence: float,
    retrieved_context: str,
    citations: list[dict],
    chat_history: list[dict],
) -> tuple[dict[str, Any], str]:
    client = get_client()
    system_prompt = _build_system_prompt()

    user_payload = {
        "role": role,
        "state": state,
        "intent": intent,
        "distance": distance,
        "confidence": confidence,
        "instructions": "Respond in German unless user asks otherwise.",
        "chat_history": chat_history,
        "retrieved_context": retrieved_context,
        "citations": citations,
        "user_input": user_input,
    }

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(user_payload, ensure_ascii=True)},
    ]

    resp = client.chat.completions.create(
        model=LANGUAGE_MODEL_NAME,
        messages=messages,
    )
    raw = resp.choices[0].message.content or ""
    return _extract_json(raw), raw


def generate_dynamic_role_questions(
    *,
    user_input: str,
    assistant_message: str,
    intent: str,
    distance: str,
    previous_questions: list[dict] | None = None,
) -> list[dict]:
    client = get_client()
    previous_questions = previous_questions or []

    question_schema = {
        "type": "object",
        "additionalProperties": False,
        "required": ["questions"],
        "properties": {
            "questions": {
                "type": "array",
                "minItems": 1,
                "maxItems": 2,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["id", "type", "prompt", "options"],
                    "properties": {
                        "id": {"type": "string"},
                        "type": {"type": "string", "enum": ["single_choice", "multi_choice", "text"]},
                        "prompt": {"type": "string"},
                        "options": {"type": "array", "items": {"type": "string"}},
                    },
                },
            }
        },
    }

    messages = [
        {
            "role": "system",
            "content": (
                "Generate dynamic role-clarification follow-up questions in German. "
                "Return STRICT JSON only with key `questions`. "
                "Questions must be user-facing and empathetic. "
                "Prefer single_choice. Max 2 questions. "
                f"Schema: {json.dumps(question_schema, ensure_ascii=True)}"
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "user_input": user_input,
                    "assistant_message": assistant_message,
                    "intent": intent,
                    "distance": distance,
                    "previous_questions": previous_questions,
                    "required_signal": "questions must help choose role for next turn",
                },
                ensure_ascii=True,
            ),
        },
    ]

    resp = client.chat.completions.create(
        model=FOLLOWUP_MODEL_NAME,
        messages=messages,
    )
    raw = resp.choices[0].message.content or ""
    data = _extract_json(raw)
    questions = data.get("questions", [])
    if not isinstance(questions, list):
        return []
    return questions[:2]


def repair_llm_json(*, invalid_output: str, error_message: str) -> tuple[dict[str, Any], str]:
    client = get_client()
    schema = as_schema_json()

    messages = [
        {
            "role": "system",
            "content": (
                "Repair the following model output into strict JSON only. "
                "Do not add explanations. Ensure schema compliance. "
                f"Schema: {schema}"
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "error": error_message,
                    "invalid_output": invalid_output,
                },
                ensure_ascii=True,
            ),
        },
    ]

    resp = client.chat.completions.create(
        model=LANGUAGE_MODEL_NAME,
        messages=messages,
    )
    raw = resp.choices[0].message.content or ""
    return _extract_json(raw), raw
