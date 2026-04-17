from __future__ import annotations

from app.domain.types import Distance, Intent, KnowledgeMode

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
    if intent == "project_specific":
        return "SWP"
    if "in unserem projekt" in text or "unsere dateien" in text:
        return "SWP"
    if "wie machen andere" in text or "andere teams" in text:
        return "SWPr"
    if intent == "pattern_mining":
        return "SKM"

    return "ESN"


def infer_knowledge_mode(user_input: str, intent: Intent, distance: Distance) -> KnowledgeMode:
    text = user_input.lower().strip()

    internalization_markers = [
        "lern", "quiz", "üb", "frage mich ab", "onboard", "einarbeiten",
        "simulation", "szenario", "feedback", "verständnis", "ideen", "brainstorm",
        "hypothese", "inspiration", "kontext", "wieder einsteigen", "re-onboarding",
        "stand", "entscheidungen", "annahmen", "hintergründe",
    ]
    combination_markers = [
        "zusammenfass", "synth", "vergleich", "vergleiche", "verbinde", "link",
        "cluster", "muster", "analys", "konzept", "kurat", "map", "überblick",
        "zusammenh", "einord", "verknüpf",
    ]
    externalization_markers = [
        "dokument", "doku", "aufschreib", "formulier", "präzisier", "unklar",
        "capture", "extrah", "rewrite", "reframe", "umform", "case", "fall",
        "brief", "draft", "entwurf", "notiz", "dokumentier", "protokoll",
    ]

    if any(marker in text for marker in internalization_markers):
        return "INTERNALIZATION"
    if any(marker in text for marker in combination_markers):
        return "COMBINATION"
    if any(marker in text for marker in externalization_markers):
        return "EXTERNALIZATION"

    if intent == "learn_mode":
        return "INTERNALIZATION"
    if intent == "pattern_mining":
        return "COMBINATION"
    if intent == "simplify":
        return "SOCIALIZATION"
    if intent == "cross_context":
        return "SOCIALIZATION"
    if intent == "project_specific" and distance == "SWP":
        return "INTERNALIZATION"

    return "SOCIALIZATION"
