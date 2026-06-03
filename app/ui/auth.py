from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from http.cookies import SimpleCookie

import streamlit as st
import streamlit.components.v1 as components

from app.backend.auth import (
    REMEMBER_ME_TTL_DAYS,
    AuthError,
    authenticate_session_token,
    authenticate_user,
    create_auth_session,
    create_user,
    revoke_auth_session,
)
from app.ui.constants import AUTH_COOKIE_NAME
from app.ui.state import clear_authenticated_user, set_authenticated_user


def render_pending_cookie_operations() -> None:
    raw_token = st.session_state.pending_auth_cookie
    if raw_token:
        _render_set_auth_cookie(raw_token)
        st.session_state.pending_auth_cookie = None

    if st.session_state.pending_auth_cookie_delete:
        _render_delete_auth_cookie()
        st.session_state.pending_auth_cookie_delete = False


def render_auth_workflow() -> bool:
    render_pending_cookie_operations()
    _restore_authenticated_user_from_cookie()

    if st.session_state.auth_user:
        return True

    st.subheader("Sign in")
    login_tab, register_tab = st.tabs(["Login", "Create account"])

    with login_tab:
        _render_login_form()

    with register_tab:
        _render_registration_form()

    st.info("Create an account or log in to use your private IKMAS workspace.")
    return False


def logout() -> None:
    revoke_auth_session(_get_auth_cookie())
    _delete_auth_cookie()
    clear_authenticated_user(st.session_state)
    st.rerun()


def _render_login_form() -> None:
    with st.form("login_form"):
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")
        remember_me = st.checkbox("Remember me", value=False, key="login_remember_me")
        submitted = st.form_submit_button("Login", type="primary")

    if not submitted:
        return

    user = authenticate_user(email, password)
    if user is None:
        st.error("Invalid email or password.")
        return

    set_authenticated_user(st.session_state, user)
    if remember_me:
        st.session_state.pending_auth_cookie = create_auth_session(user.user_id)
    st.success(f"Welcome back, {user.name}.")
    st.rerun()


def _render_registration_form() -> None:
    with st.form("register_form"):
        name = st.text_input("Name", key="register_name")
        email = st.text_input("Email", key="register_email")
        password = st.text_input("Password", type="password", key="register_password")
        confirm_password = st.text_input(
            "Confirm password",
            type="password",
            key="register_confirm_password",
        )
        submitted = st.form_submit_button("Create account", type="primary")

    if not submitted:
        return

    if password != confirm_password:
        st.error("Passwords do not match.")
        return

    try:
        user = create_user(name, email, password)
    except AuthError as exc:
        st.error(str(exc))
        return

    set_authenticated_user(st.session_state, user)
    st.success(f"Account created for {user.name}.")
    st.rerun()


def _restore_authenticated_user_from_cookie() -> None:
    if st.session_state.auth_user or st.session_state.auth_cookie_checked:
        return

    st.session_state.auth_cookie_checked = True
    raw_token = _get_auth_cookie()
    if not raw_token:
        return

    user = authenticate_session_token(raw_token)
    if user is None:
        _delete_auth_cookie()
        return

    set_authenticated_user(st.session_state, user, reset_chat_history=False)
    st.rerun()


def _get_auth_cookie() -> str | None:
    return st.context.cookies.get(AUTH_COOKIE_NAME)


def _delete_auth_cookie() -> None:
    st.session_state.pending_auth_cookie_delete = True


def _render_set_auth_cookie(raw_token: str) -> None:
    expires_at = datetime.now(UTC) + timedelta(days=REMEMBER_ME_TTL_DAYS)
    cookie = SimpleCookie()
    cookie[AUTH_COOKIE_NAME] = raw_token
    cookie[AUTH_COOKIE_NAME]["path"] = "/"
    cookie[AUTH_COOKIE_NAME]["expires"] = expires_at.strftime("%a, %d %b %Y %H:%M:%S GMT")
    cookie[AUTH_COOKIE_NAME]["samesite"] = "Strict"
    components.html(
        f"<script>document.cookie = {json.dumps(cookie.output(header='').strip())};</script>",
        height=0,
    )


def _render_delete_auth_cookie() -> None:
    expired_cookie = (
        f"{AUTH_COOKIE_NAME}=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT; SameSite=Strict"
    )
    components.html(
        f"<script>document.cookie = {json.dumps(expired_cookie)};</script>",
        height=0,
    )
