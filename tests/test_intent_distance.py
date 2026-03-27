import pytest

from app.backend.intent_distance import classify_intent, estimate_distance


@pytest.mark.parametrize(
    ("user_input", "expected"),
    [
        ("Mach ein Quiz mit mir", "learn_mode"),
        ("Was ist Retrieval-Augmented Generation?", "what_is"),
        ("Erklar es bitte einfach fur Anfanger", "simplify"),
        ("Wie funktioniert das in unserem Projekt?", "project_specific"),
        ("Wie machen andere Teams das als Best Practice?", "cross_context"),
        ("Analysiere Muster und finde Konzepte", "pattern_mining"),
        ("Irgendeine offene Frage ohne Marker", "what_is"),
    ],
)
def test_classify_intent_matches_expected_branch(user_input, expected):
    assert classify_intent(user_input) == expected


@pytest.mark.parametrize("intent", ["what_is", "simplify", "learn_mode"])
def test_estimate_distance_returns_esn_for_learning_intents(intent):
    assert estimate_distance("in unserem projekt bitte", intent) == "ESN"


def test_estimate_distance_returns_swp_for_project_context():
    assert estimate_distance("Wie ist das in unserem Projekt umgesetzt?", "project_specific") == "SWP"


def test_estimate_distance_returns_swpr_for_cross_context():
    assert estimate_distance("Wie machen andere Teams das?", "cross_context") == "SWPr"


def test_estimate_distance_returns_skm_for_pattern_mining():
    assert estimate_distance("Analysiere bitte die Signale", "pattern_mining") == "SKM"


def test_estimate_distance_falls_back_to_esn():
    assert estimate_distance("Ganz allgemeine Frage", "project_specific") == "ESN"
