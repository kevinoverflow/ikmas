from __future__ import annotations

import json
from typing import Any

from app.backend.llm_client import generate_dynamic_role_questions
from app.backend.schema import validate_or_raise

ROLE_GATE_QUESTION_GOAL = {
    "id": "rg_goal",
    "type": "single_choice",
    "prompt": "Was ist dein Hauptziel für diese Anfrage?",
    "options": ["verstehen", "projektkontext", "vergleich", "musteranalyse"],
}

ROLE_GATE_QUESTION_MODE = {
    "id": "rg_mode",
    "type": "single_choice",
    "prompt": "Welchen Unterstützungsmodus möchtest du?",
    "options": ["erklaeren", "tutoring", "dokumentieren"],
}


def parse_role_gate_answers(user_input: str) -> dict[str, Any] | None:
    text = (user_input or "").strip()
    if not text.startswith("{"):
        return None

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None

    answers = data.get("role_gate_answers")
    return answers if isinstance(answers, dict) else None


def _extract_answer(value: Any) -> str:
    if isinstance(value, list):
        for item in value:
            if isinstance(item, str) and item.strip():
                return item.strip().lower()
        return ""
    if isinstance(value, str):
        return value.strip().lower()
    return ""


def infer_role_from_gate_answers(role_gate_answers: dict[str, Any]) -> str:
    goal = _extract_answer(role_gate_answers.get("rg_goal"))
    mode = _extract_answer(role_gate_answers.get("rg_mode"))

    if mode == "tutoring":
        return "TutoringAgent"
    if goal == "musteranalyse":
        return "ConceptMiningAgent"
    if mode == "dokumentieren" or goal == "projektkontext":
        return "DigitalMemoryAgent"
    return "MentorAgent"


def infer_intent_distance_from_gate_answers(role_gate_answers: dict[str, Any]) -> tuple[str, str]:
    goal = _extract_answer(role_gate_answers.get("rg_goal"))
    mode = _extract_answer(role_gate_answers.get("rg_mode"))

    if mode == "tutoring":
        return "learn_mode", "ESN"
    if goal == "musteranalyse":
        return "pattern_mining", "SKM"
    if goal == "vergleich":
        return "cross_context", "SWPr"
    if goal == "projektkontext" or mode == "dokumentieren":
        return "project_specific", "SWP"
    return "what_is", "ESN"


def should_open_role_gate(intent: str, session_ctx: dict[str, Any], role_override: str | None, role_gate_answers: dict[str, Any] | None) -> bool:
    if role_override:
        return False
    if role_gate_answers:
        return False
    if bool(session_ctx.get("pending_role_gate", False)):
        return True
    # project_specific is the classifier fallback and often ambiguous.
    return intent == "project_specific"


def role_gate_payload(message: str = "Damit ich die passende Rolle waehlen kann, beantworte bitte kurz diese zwei Rueckfragen.") -> dict[str, Any]:
    payload = {
        "mode": "role_clarification",
        "interaction_phase": "ROLE_GATE",
        "role": "RoleGate",
        "state": None,
        "assistant_message": message,
        "questions": [ROLE_GATE_QUESTION_GOAL, ROLE_GATE_QUESTION_MODE],
        "artefacts": [],
        "actions": [],
        "citations": [],
        "telemetry": {"confidence": 0.0, "needs_followup": True},
    }
    return validate_or_raise(payload)


def default_role_questions() -> list[dict[str, Any]]:
    return [ROLE_GATE_QUESTION_GOAL, ROLE_GATE_QUESTION_MODE]


def build_post_response_role_questions(
    *,
    user_input: str,
    assistant_message: str,
    intent: str,
    distance: str,
    role_gate_answers: dict[str, Any] | None,
    role_override: str | None,
    previous_questions: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    # If user explicitly chose role or already answered role gate in this turn,
    # do not re-ask role assignment questions.
    if role_override or role_gate_answers:
        return []

    try:
        questions = generate_dynamic_role_questions(
            user_input=user_input,
            assistant_message=assistant_message,
            intent=intent,
            distance=distance,
            previous_questions=previous_questions or [],
        )
    except Exception:
        questions = []

    if not questions:
        questions = default_role_questions()

    out: list[dict[str, Any]] = []
    for q in questions[:2]:
        if not isinstance(q, dict):
            continue
        qid = str(q.get("id", "")).strip() or "rg_dynamic"
        qtype = str(q.get("type", "single_choice")).strip()
        prompt = str(q.get("prompt", "")).strip()
        options = q.get("options", [])
        if not isinstance(options, list):
            options = []
        options = [str(o) for o in options]
        if not prompt:
            continue
        if qtype not in {"single_choice", "multi_choice", "text"}:
            qtype = "single_choice"
        out.append({"id": qid, "type": qtype, "prompt": prompt, "options": options})

    return out or default_role_questions()
