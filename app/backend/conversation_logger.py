from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from app.infrastructure.config import CONVERSATION_LOG_PATH


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe(obj: Any) -> Any:
    try:
        json.dumps(obj, ensure_ascii=True)
        return obj
    except TypeError:
        return str(obj)


def log_conversation_event(
    *,
    session_id: str,
    user_id: str | None,
    user_message: str,
    payload: dict[str, Any],
    system_state: dict[str, Any],
    role_override: str | None = None,
) -> None:
    CONVERSATION_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    event = {
        "timestamp": _utc_now(),
        "event_type": "assistant_turn",
        "session_id": session_id,
        "user_id": user_id or "anonymous",
        "role_override": role_override,
        "user_message": user_message,
        "mode": payload.get("mode"),
        "interaction_phase": payload.get("interaction_phase"),
        "role": payload.get("role"),
        "state": payload.get("state"),
        "assistant_message": payload.get("assistant_message"),
        "telemetry": payload.get("telemetry", {}),
        "counts": {
            "questions": len(payload.get("questions", [])),
            "artefacts": len(payload.get("artefacts", [])),
            "citations": len(payload.get("citations", [])),
            "actions": len(payload.get("actions", [])),
        },
        "system_state": system_state,
    }

    with CONVERSATION_LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(_safe(event), ensure_ascii=True) + "\n")
        f.flush()
