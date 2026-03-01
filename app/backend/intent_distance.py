from __future__ import annotations


def _normalize(text: str) -> str:
    return (text or "").strip().lower()


def classify_intent(user_input: str) -> str:
    text = _normalize(user_input)

    if any(token in text for token in ["lernmodus", "lern mode", "learning mode", "teach me", "übe", "quiz"]):
        return "learn_mode"
    if text.startswith("was ist") or "was ist" in text:
        return "what_is"
    if "einfach erklären" in text or "einfach erklaeren" in text or "für anfänger" in text:
        return "simplify"
    if "in unserem projekt" in text or "bei uns" in text:
        return "project_specific"
    if "wie machen andere" in text or "andere teams" in text or "best practices" in text:
        return "cross_context"
    if "analysiere muster" in text or "muster" in text or "pattern" in text:
        return "pattern_mining"
    return "project_specific"


def estimate_distance(user_input: str, user_profile: dict | None = None) -> str:
    text = _normalize(user_input)

    if text.startswith("was ist") or "einfach erklären" in text or "einfach erklaeren" in text:
        return "ESN"
    if "in unserem projekt" in text or "bei uns" in text:
        return "SWP"
    if "wie machen andere" in text or "andere teams" in text:
        return "SWPr"
    if "analysiere muster" in text or "pattern" in text or "muster" in text:
        return "SKM"

    if user_profile and user_profile.get("role") == "novice":
        return "ESN"

    return "SWP"
