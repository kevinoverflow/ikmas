import pytest

from app.domain.types import InternalizationState, SECIPhase
from app.infrastructure import db
from app.services.seci_workflow_service import SECIWorkflowService


@pytest.fixture()
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "ikmas_test.db")
    db.init_db()


def test_seci_session_progression(temp_db):
    svc = SECIWorkflowService()
    created = svc.start_session("user-1", phase=SECIPhase.SOCIALIZATION)
    session_id = created["session_id"]

    after_phase = svc.apply_event(session_id, event_type="advance_phase")
    assert after_phase["phase"] == SECIPhase.EXTERNALIZATION.value

    svc.apply_event(session_id, event_type="advance_phase")
    to_internal = svc.apply_event(session_id, event_type="advance_phase")
    assert to_internal["phase"] == SECIPhase.INTERNALIZATION.value
    assert to_internal["internalization_state"] == InternalizationState.ASSESS.value

    advanced = svc.apply_event(session_id, event_type="advance_internalization")
    assert advanced["internalization_state"] == InternalizationState.EXPLAIN.value


def test_seci_invalid_transition_raises(temp_db):
    svc = SECIWorkflowService()
    created = svc.start_session("user-1", phase=SECIPhase.SOCIALIZATION)
    with pytest.raises(ValueError):
        svc.apply_event(
            created["session_id"],
            event_type="set_phase",
            target_phase=SECIPhase.COMBINATION,
        )
