import json

from app.backend import conversation_logger


def test_log_conversation_event_writes_jsonl(tmp_path, monkeypatch):
    log_path = tmp_path / "conversation_events.jsonl"
    monkeypatch.setattr(conversation_logger, "CONVERSATION_LOG_PATH", log_path)

    conversation_logger.log_conversation_event(
        session_id="s1",
        user_id="u1",
        user_message="Was ist RAG?",
        role_override=None,
        payload={
            "mode": "assistant_response",
            "interaction_phase": "ASSISTANT",
            "role": "MentorAgent",
            "state": None,
            "assistant_message": "RAG ist ...",
            "questions": [{"id": "rg_goal"}],
            "artefacts": [],
            "actions": [],
            "citations": [{"source_id": "doc#1", "score": 0.7}],
            "telemetry": {"confidence": 0.7, "needs_followup": True},
        },
        system_state={"intent": "what_is", "distance": "ESN"},
    )

    assert log_path.exists()
    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    event = json.loads(lines[0])
    assert event["session_id"] == "s1"
    assert event["role"] == "MentorAgent"
    assert event["counts"]["questions"] == 1
