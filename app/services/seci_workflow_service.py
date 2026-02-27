from __future__ import annotations

from typing import Dict, Optional
from uuid import uuid4

from app.domain.types import InternalizationState, SECIPhase
from app.infrastructure.db import db_cursor
from app.services.contracts import SECIWorkflowServiceContract

NEXT_PHASE = {
    SECIPhase.SOCIALIZATION: SECIPhase.EXTERNALIZATION,
    SECIPhase.EXTERNALIZATION: SECIPhase.COMBINATION,
    SECIPhase.COMBINATION: SECIPhase.INTERNALIZATION,
}

NEXT_INTERNALIZATION_STATE = {
    InternalizationState.ASSESS: InternalizationState.EXPLAIN,
    InternalizationState.EXPLAIN: InternalizationState.CHECK,
    InternalizationState.CHECK: InternalizationState.PRACTICE,
    InternalizationState.PRACTICE: InternalizationState.FEEDBACK,
    InternalizationState.FEEDBACK: InternalizationState.SCHEDULE,
}


class SECIWorkflowService(SECIWorkflowServiceContract):
    def start_session(self, user_id: str, phase: SECIPhase = SECIPhase.SOCIALIZATION) -> Dict[str, str]:
        session_id = str(uuid4())
        state = InternalizationState.ASSESS.value if phase == SECIPhase.INTERNALIZATION else None
        with db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO seci_sessions (id, user_id, phase, internalization_state)
                VALUES (?, ?, ?, ?)
                """,
                (session_id, user_id, phase.value, state),
            )
            cur.execute(
                """
                INSERT INTO seci_transitions (session_id, event_type, to_phase, to_state, reason)
                VALUES (?, 'session_start', ?, ?, ?)
                """,
                (session_id, phase.value, state, "Session created"),
            )
        return {"session_id": session_id, "phase": phase.value, "internalization_state": state}

    def get_session(self, session_id: str) -> Dict[str, object]:
        with db_cursor() as cur:
            cur.execute("SELECT * FROM seci_sessions WHERE id = ?", (session_id,))
            session = cur.fetchone()
            if not session:
                raise ValueError(f"Unknown session_id: {session_id}")
            cur.execute(
                """
                SELECT event_type, from_phase, to_phase, from_state, to_state, reason, created_at
                FROM seci_transitions
                WHERE session_id = ?
                ORDER BY id ASC
                """,
                (session_id,),
            )
            transitions = [dict(r) for r in cur.fetchall()]
        result = dict(session)
        result["transitions"] = transitions
        return result

    def apply_event(
        self,
        session_id: str,
        event_type: str,
        target_phase: Optional[SECIPhase] = None,
        target_state: Optional[InternalizationState] = None,
        reason: str = "",
    ) -> Dict[str, object]:
        with db_cursor() as cur:
            cur.execute("SELECT * FROM seci_sessions WHERE id = ?", (session_id,))
            row = cur.fetchone()
            if not row:
                raise ValueError(f"Unknown session_id: {session_id}")

            current_phase = SECIPhase(row["phase"])
            current_state = (
                InternalizationState(row["internalization_state"]) if row["internalization_state"] else None
            )

            new_phase = current_phase
            new_state = current_state

            if event_type == "advance_phase":
                expected_next = NEXT_PHASE.get(current_phase)
                if expected_next is None:
                    raise ValueError(f"Phase {current_phase.value} cannot be advanced.")
                if target_phase and target_phase != expected_next:
                    raise ValueError(
                        f"Invalid phase transition {current_phase.value}->{target_phase.value}. Expected {expected_next.value}."
                    )
                new_phase = expected_next
                new_state = InternalizationState.ASSESS if new_phase == SECIPhase.INTERNALIZATION else None
            elif event_type == "set_phase":
                if not target_phase:
                    raise ValueError("target_phase is required for set_phase.")
                allowed = target_phase == current_phase or NEXT_PHASE.get(current_phase) == target_phase
                if not allowed:
                    raise ValueError(
                        f"Invalid phase transition {current_phase.value}->{target_phase.value}."
                    )
                new_phase = target_phase
                new_state = InternalizationState.ASSESS if new_phase == SECIPhase.INTERNALIZATION else None
            elif event_type == "advance_internalization":
                if current_phase != SECIPhase.INTERNALIZATION:
                    raise ValueError("Internalization state transitions require internalization phase.")
                if current_state is None:
                    current_state = InternalizationState.ASSESS
                expected_next_state = NEXT_INTERNALIZATION_STATE.get(current_state)
                if expected_next_state is None:
                    raise ValueError(f"State {current_state.value} cannot be advanced.")
                if target_state and target_state != expected_next_state:
                    raise ValueError(
                        f"Invalid state transition {current_state.value}->{target_state.value}. Expected {expected_next_state.value}."
                    )
                new_state = expected_next_state
            elif event_type == "set_internalization_state":
                if current_phase != SECIPhase.INTERNALIZATION:
                    raise ValueError("set_internalization_state requires internalization phase.")
                if not target_state:
                    raise ValueError("target_state is required for set_internalization_state.")
                if current_state is None:
                    current_state = InternalizationState.ASSESS
                allowed = target_state == current_state or NEXT_INTERNALIZATION_STATE.get(current_state) == target_state
                if not allowed:
                    raise ValueError(
                        f"Invalid state transition {current_state.value}->{target_state.value}."
                    )
                new_state = target_state
            else:
                raise ValueError(f"Unknown event_type: {event_type}")

            cur.execute(
                """
                UPDATE seci_sessions
                SET phase = ?, internalization_state = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (new_phase.value, new_state.value if new_state else None, session_id),
            )
            cur.execute(
                """
                INSERT INTO seci_transitions (
                    session_id, event_type, from_phase, to_phase, from_state, to_state, reason
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    event_type,
                    current_phase.value,
                    new_phase.value,
                    current_state.value if current_state else None,
                    new_state.value if new_state else None,
                    reason,
                ),
            )

        return self.get_session(session_id)
