import json

from app.backend import sqlite_store
from app.backend.sqlite_store import TurnRecord


def test_init_and_log_turn(tmp_path, monkeypatch):
    db_path = tmp_path / "ikmas.db"
    monkeypatch.setattr(sqlite_store, "SQLITE_DB_PATH", db_path)

    sqlite_store.init_db()
    sqlite_store.create_session("s1")

    sqlite_store.log_turn(
        TurnRecord(
            session_id="s1",
            user_message="hello",
            chosen_role="MentorAgent",
            retrieval_confidence=0.7,
            system_state={"x": 1},
            llm_json={
                "mode": "assistant_response",
                "interaction_phase": "ASSISTANT",
                "role": "MentorAgent",
                "state": None,
                "assistant_message": "ok",
                "questions": [],
                "artefacts": [],
                "actions": [],
                "citations": [],
                "telemetry": {"confidence": 0.7, "needs_followup": True},
            },
        )
    )

    latest = sqlite_store.get_latest_turn("s1")
    assert latest is not None
    assert latest["turn_id"] == 1
    assert latest["chosen_role"] == "MentorAgent"
    assert latest["system_state"]["x"] == 1


def test_save_artefacts_and_links(tmp_path, monkeypatch):
    db_path = tmp_path / "ikmas.db"
    monkeypatch.setattr(sqlite_store, "SQLITE_DB_PATH", db_path)
    sqlite_store.init_db()

    ids = sqlite_store.save_artefacts(
        [{"type": "summary", "title": "t", "body_md": "b", "tags": ["x"]}],
        project="default",
        refs=[{"source_id": "doc#1", "score": 0.4}],
    )
    assert len(ids) == 1

    sqlite_store.save_links("artefact", str(ids[0]), "source", "doc#1", "supports", 0.4)

    with sqlite_store._connect() as conn:
        row = conn.execute("SELECT COUNT(*) AS c FROM links").fetchone()
        assert row["c"] == 1
