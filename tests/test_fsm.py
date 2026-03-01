from app.backend.fsm import decide_state


def test_non_tutoring_returns_none():
    assert decide_state("MentorAgent", 0.9, {}) is None


def test_tutoring_start_low_confidence_assess():
    assert decide_state("TutoringAgent", 0.5, {}) == "ASSESS"


def test_tutoring_start_high_confidence_explain():
    assert decide_state("TutoringAgent", 0.8, {}) == "EXPLAIN"


def test_tutoring_transitions():
    assert decide_state("TutoringAgent", 0.8, {"last_state": "ASSESS"}) == "EXPLAIN"
    assert decide_state("TutoringAgent", 0.8, {"last_state": "EXPLAIN"}) == "CHECK"
    assert decide_state("TutoringAgent", 0.8, {"last_state": "CHECK"}) == "PRACTICE"
