from types import SimpleNamespace

from app.backend import orchestrator


def _fake_valid_payload(role="TutoringAgent", state="ASSESS"):
    return {
        "role": role,
        "state": state,
        "assistant_message": "ok",
        "questions": [],
        "artefacts": [],
        "actions": [{"type": "RETRIEVE", "query": "x", "filters": {"project": "default"}}],
        "citations": [{"source_id": "doc#1", "score": 0.6}],
        "telemetry": {"confidence": 0.3, "needs_followup": True},
    }


def _fake_role_questions(*args, **kwargs):
    return [
        {
            "id": "rg_goal",
            "type": "single_choice",
            "prompt": "Was ist dein Hauptziel?",
            "options": ["verstehen", "projektkontext", "vergleich", "musteranalyse"],
        }
    ]


def test_handle_turn_low_confidence_enters_assess(monkeypatch):
    monkeypatch.setattr(orchestrator, "init_db", lambda: None)
    monkeypatch.setattr(orchestrator, "create_session", lambda session_id: None)
    monkeypatch.setattr(orchestrator, "get_user_profile", lambda user_id: {"role": "member"})
    monkeypatch.setattr(orchestrator, "get_session_context", lambda session_id: {})
    monkeypatch.setattr(orchestrator, "get_recent_turns", lambda session_id, limit=5: [])
    monkeypatch.setattr(orchestrator, "persist_artefacts_with_links", lambda artefacts, citations, project="default": [])

    retrieval = SimpleNamespace(docs=[], confidence=0.2, top1=0.0, avg_top3=0.0, coverage=0.0)
    monkeypatch.setattr(orchestrator, "retrieve_bundle", lambda **kwargs: retrieval)

    monkeypatch.setattr(orchestrator, "classify_intent", lambda text: "learn_mode")
    monkeypatch.setattr(orchestrator, "estimate_distance", lambda text, profile: "ESN")
    monkeypatch.setattr(orchestrator, "route_role", lambda **kwargs: "TutoringAgent")
    monkeypatch.setattr(orchestrator, "decide_state", lambda **kwargs: "ASSESS")
    monkeypatch.setattr(orchestrator, "call_llm_json", lambda **kwargs: (_fake_valid_payload(), "{}"))
    monkeypatch.setattr(orchestrator, "build_post_response_role_questions", _fake_role_questions)

    logged = {}

    def _log_turn(rec):
        logged["record"] = rec

    monkeypatch.setattr(orchestrator, "log_turn", _log_turn)

    payload = orchestrator.handle_turn("s1", "frage", user_id="u1")
    assert payload["state"] == "ASSESS"
    assert payload["role"] == "TutoringAgent"
    assert payload["interaction_phase"] == "ASSISTANT"
    assert payload["mode"] == "assistant_response"
    assert payload["questions"][0]["id"] == "rg_goal"
    assert logged["record"].retrieval_confidence == 0.2


def test_handle_turn_repairs_or_fallbacks(monkeypatch):
    monkeypatch.setattr(orchestrator, "init_db", lambda: None)
    monkeypatch.setattr(orchestrator, "create_session", lambda session_id: None)
    monkeypatch.setattr(orchestrator, "get_user_profile", lambda user_id: {"role": "member"})
    monkeypatch.setattr(orchestrator, "get_session_context", lambda session_id: {})
    monkeypatch.setattr(orchestrator, "get_recent_turns", lambda session_id, limit=5: [])
    monkeypatch.setattr(orchestrator, "persist_artefacts_with_links", lambda artefacts, citations, project="default": [])
    monkeypatch.setattr(
        orchestrator,
        "retrieve_bundle",
        lambda **kwargs: SimpleNamespace(docs=[], confidence=0.9, top1=0.8, avg_top3=0.8, coverage=1.0),
    )
    monkeypatch.setattr(orchestrator, "classify_intent", lambda text: "what_is")
    monkeypatch.setattr(orchestrator, "estimate_distance", lambda text, profile: "ESN")
    monkeypatch.setattr(orchestrator, "route_role", lambda **kwargs: "MentorAgent")
    monkeypatch.setattr(orchestrator, "decide_state", lambda **kwargs: None)
    monkeypatch.setattr(orchestrator, "call_llm_json", lambda **kwargs: (_ for _ in ()).throw(RuntimeError("bad")))
    monkeypatch.setattr(orchestrator, "repair_llm_json", lambda **kwargs: (_ for _ in ()).throw(RuntimeError("still bad")))
    monkeypatch.setattr(orchestrator, "build_post_response_role_questions", _fake_role_questions)
    monkeypatch.setattr(orchestrator, "log_turn", lambda rec: None)

    payload = orchestrator.handle_turn("s2", "frage", user_id="u1")
    assert payload["role"] == "MentorAgent"
    assert payload["state"] is None
    assert payload["interaction_phase"] == "ASSISTANT"
    assert payload["mode"] == "assistant_response"
    assert payload["questions"][0]["id"] == "rg_goal"
    assert payload["telemetry"]["confidence"] == 0.9


def test_handle_turn_role_gate_answers_influence_role(monkeypatch):
    monkeypatch.setattr(orchestrator, "init_db", lambda: None)
    monkeypatch.setattr(orchestrator, "create_session", lambda session_id: None)
    monkeypatch.setattr(orchestrator, "get_user_profile", lambda user_id: {"role": "member"})
    monkeypatch.setattr(orchestrator, "get_session_context", lambda session_id: {})
    monkeypatch.setattr(orchestrator, "get_recent_turns", lambda session_id, limit=5: [])
    monkeypatch.setattr(orchestrator, "persist_artefacts_with_links", lambda artefacts, citations, project="default": [])
    monkeypatch.setattr(orchestrator, "retrieve_bundle", lambda **kwargs: SimpleNamespace(docs=[], confidence=0.7, top1=0.7, avg_top3=0.7, coverage=1.0))
    monkeypatch.setattr(orchestrator, "classify_intent", lambda text: "project_specific")
    monkeypatch.setattr(orchestrator, "estimate_distance", lambda text, profile: "SWP")
    monkeypatch.setattr(orchestrator, "route_role", lambda **kwargs: "TutoringAgent")
    monkeypatch.setattr(orchestrator, "decide_state", lambda **kwargs: "ASSESS")
    monkeypatch.setattr(orchestrator, "call_llm_json", lambda **kwargs: (_fake_valid_payload(role="TutoringAgent", state="ASSESS"), "{}"))
    monkeypatch.setattr(orchestrator, "build_post_response_role_questions", lambda **kwargs: [])
    monkeypatch.setattr(orchestrator, "log_turn", lambda rec: None)

    payload = orchestrator.handle_turn(
        "s4",
        '{"role_gate_answers": {"rg_goal": "verstehen", "rg_mode": "tutoring"}}',
        user_id="u1",
    )
    assert payload["interaction_phase"] == "ASSISTANT"
    assert payload["mode"] == "assistant_response"
    assert payload["role"] == "TutoringAgent"


def test_handle_turn_role_override_skips_dynamic_role_questions(monkeypatch):
    monkeypatch.setattr(orchestrator, "init_db", lambda: None)
    monkeypatch.setattr(orchestrator, "create_session", lambda session_id: None)
    monkeypatch.setattr(orchestrator, "get_user_profile", lambda user_id: {"role": "member"})
    monkeypatch.setattr(orchestrator, "get_session_context", lambda session_id: {})
    monkeypatch.setattr(orchestrator, "get_recent_turns", lambda session_id, limit=5: [])
    monkeypatch.setattr(orchestrator, "persist_artefacts_with_links", lambda artefacts, citations, project="default": [])
    monkeypatch.setattr(orchestrator, "retrieve_bundle", lambda **kwargs: SimpleNamespace(docs=[], confidence=0.7, top1=0.7, avg_top3=0.7, coverage=1.0))
    monkeypatch.setattr(orchestrator, "classify_intent", lambda text: "project_specific")
    monkeypatch.setattr(orchestrator, "estimate_distance", lambda text, profile: "SWP")
    monkeypatch.setattr(orchestrator, "decide_state", lambda **kwargs: None)
    monkeypatch.setattr(orchestrator, "call_llm_json", lambda **kwargs: (_fake_valid_payload(role="MentorAgent", state=None), "{}"))
    monkeypatch.setattr(orchestrator, "build_post_response_role_questions", lambda **kwargs: [])
    monkeypatch.setattr(orchestrator, "log_turn", lambda rec: None)

    payload = orchestrator.handle_turn("s5", "in unserem projekt", user_id="u1", role_override="MentorAgent")
    assert payload["interaction_phase"] == "ASSISTANT"
    assert payload["role"] == "MentorAgent"
