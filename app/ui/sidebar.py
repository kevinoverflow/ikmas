from __future__ import annotations

import streamlit as st

from app.backend.llm_client import get_client
from app.infrastructure.config import LLM_MODEL_NAME
from app.ui.session_history import list_recent_chat_sessions, load_session_chat_history
from app.ui.state import reset_chat


def render_sidebar(current_user: dict, on_logout) -> None:
    with st.sidebar:
        _render_account(current_user, on_logout)
        st.divider()
        _render_chat_navigation(current_user["id"])
        st.divider()
        _render_model_information()


def _render_account(current_user: dict, on_logout) -> None:
    st.header("Account")
    st.write(f"**{current_user['name']}**")
    st.caption(current_user["email"])
    st.caption(f"User ID: {current_user['id']}")
    if st.button("Log out", type="secondary"):
        on_logout()


def _render_chat_navigation(user_id: str) -> None:
    st.header("Chats")

    if st.button("New chat", type="primary", use_container_width=True):
        reset_chat(st.session_state)
        st.rerun()

    try:
        sessions = list_recent_chat_sessions(user_id)
    except Exception as exc:
        st.caption(f"Error reading chats: {exc}")
    else:
        if sessions:
            for session in sessions:
                _render_chat_session_button(session, user_id)
        else:
            st.caption("No chats yet.")

    _render_session_debug(user_id)


def _render_chat_session_button(session, user_id: str) -> None:
    button_type = "primary" if session.session_id == st.session_state.session_id else "secondary"
    if st.button(
        session.display_title,
        key=f"chat::{session.session_id}",
        type=button_type,
        use_container_width=True,
    ):
        st.session_state.session_id = session.session_id
        st.session_state.chat_history = load_session_chat_history(session.session_id, user_id)
        st.rerun()


def _render_session_debug(user_id: str) -> None:
    with st.expander("Session debug"):
        st.caption("Current session ID:")
        st.code(st.session_state.session_id)

        new_session_id = st.text_input(
            "New Session ID:",
            value="",
            placeholder="Enter a custom session ID",
        )
        if st.button("Switch to Session", type="secondary") and new_session_id:
            st.session_state.session_id = new_session_id
            st.session_state.chat_history = load_session_chat_history(new_session_id, user_id)
            st.success(f"Switched to session: {new_session_id}")
            st.rerun()

        if st.button("Clear Session History"):
            st.session_state.chat_history = []
            st.success("Session history cleared")
            st.rerun()


def _render_model_information() -> None:
    st.header("Model Information")
    try:
        client = get_client()
        models = client.models.list()
        model_ids = [model.id for model in models.data]
        
        # Add model selection dropdown
        selected_model = st.selectbox(
            "Select LLM Model:",
            model_ids,
            index=model_ids.index(LLM_MODEL_NAME) if LLM_MODEL_NAME in model_ids else 0,
            key="model_selector"
        )
        
        # Store selected model in session state
        st.session_state.selected_model = selected_model
        
        st.divider()
        st.caption(f"Selected Model: {selected_model}")
        
    except Exception as exc:
        st.warning(f"Could not list models: {exc}")
        # Fallback to default model
        st.caption(f"Chat model: {LLM_MODEL_NAME}")
