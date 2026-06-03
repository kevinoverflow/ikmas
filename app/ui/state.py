from __future__ import annotations

import uuid


def init_session_state(session_state) -> None:
    defaults = {
        "auth_user": None,
        "chat_history": [],
        "docs_indexed": False,
        "session_id": str(uuid.uuid4()),
        "auth_cookie_checked": False,
        "pending_auth_cookie": None,
        "pending_auth_cookie_delete": False,
    }

    for key, value in defaults.items():
        if key not in session_state:
            session_state[key] = value


def reset_chat(session_state) -> None:
    session_state.session_id = str(uuid.uuid4())
    session_state.chat_history = []


def set_authenticated_user(session_state, user, *, reset_chat_history: bool = True) -> None:
    session_state.auth_user = {
        "id": user.user_id,
        "name": user.name,
        "email": user.email,
    }
    if reset_chat_history:
        reset_chat(session_state)


def clear_authenticated_user(session_state) -> None:
    session_state.auth_user = None
    session_state.auth_cookie_checked = False
    reset_chat(session_state)
