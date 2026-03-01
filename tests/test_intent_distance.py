from app.backend.intent_distance import classify_intent, estimate_distance


def test_intent_rules():
    assert classify_intent("Was ist RAG?") == "what_is"
    assert classify_intent("Kannst du das einfach erklären?") == "simplify"
    assert classify_intent("In unserem Projekt wie nutzen wir das?") == "project_specific"
    assert classify_intent("Wie machen andere Teams das?") == "cross_context"
    assert classify_intent("Analysiere Muster in den Tickets") == "pattern_mining"


def test_distance_rules():
    assert estimate_distance("Was ist X?") == "ESN"
    assert estimate_distance("In unserem Projekt bitte") == "SWP"
    assert estimate_distance("Wie machen andere das") == "SWPr"
    assert estimate_distance("Analysiere Muster") == "SKM"
