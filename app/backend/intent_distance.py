from __future__ import annotations
from app.domain.types import Intent, Distance

def classify_intent(user_input: str) -> Intent:
    text = user_input.lower().strip()

    if any(x in text for x in ["lern", "prüf mich", "quiz", "üb", "frage mich ab"]):
        return "learn_mode" 
    if any(x in text for x in ["was ist", "erkläre", "definition", "bedeutet"]):
        return "what_is"
    if any(x in text for x in ["einfach", "vereinfacht", "verständlich", "für anfänger"]):
        return "simplify"
    if any(x in text for x in ["in unserem projekt", "bei uns", "unsere doku", "unsere dateien"]):
        return "project_specific"
    if any(x in text for x in ["wie machen andere", "best practice", "vergleich mit anderen"]):
        return "cross_context"
    if any(x in text for x in ["muster", "cluster", "analysiere", "finde konzepte", "signal"]):
        return "pattern_mining"

    return "what_is"


def estimate_distance(user_input: str, intent: str) -> Distance:
    text = user_input.lower().strip()

    if intent in {"what_is", "simplify", "learn_mode"}:
        return "ESN"
    if "in unserem projekt" in text or "unsere dateien" in text:
        return "SWP"
    if "wie machen andere" in text or "andere teams" in text:
        return "SWPr"
    if intent == "pattern_mining":
        return "SKM"

    return "ESN"