from __future__ import annotations

import streamlit as st

from app.backend.router_agent import model_selection_for_role


def render_chat(current_user: dict, collection_id: str) -> None:
    st.markdown("---")
    query = st.chat_input("Ask a question about your files:")

    if query:
        _handle_query(query, current_user, collection_id)

    for turn in st.session_state.chat_history:
        _render_chat_turn(turn)


def _handle_query(query: str, current_user: dict, collection_id: str) -> None:
    with st.spinner("Thinking..."):
        try:
            payload = _ask_assistant(query, current_user, collection_id)
        except Exception as exc:
            st.error(f"Error: {exc}")
            st.stop()

    st.session_state.chat_history.append({"user": query, "payload": payload})


def _ask_assistant(question: str, current_user: dict, collection_id: str):
    from app.backend.orchestrator import handle_turn

    return handle_turn(
        session_id=st.session_state.session_id,
        user_input=question,
        user_id=current_user["id"],
        collection_name=collection_id,
        chat_history=_format_chat_history_for_backend(st.session_state.chat_history),
    )


def _format_chat_history_for_backend(chat_history: list[dict]) -> list[dict]:
    turns = []
    for turn in chat_history:
        payload = turn.get("payload", {})
        turns.append(
            {
                "user": turn.get("user", ""),
                "assistant": payload.get("assistant_message", ""),
            }
        )
    return turns


def _render_chat_turn(turn: dict) -> None:
    st.chat_message("user").markdown(turn["user"])
    payload = turn["payload"]
    telemetry = payload.get("telemetry", {})

    with st.chat_message("assistant"):
        st.markdown(payload["assistant_message"])
        _render_response_meta(payload, telemetry)
        _render_questions(payload.get("questions", []))
        _render_artefacts(payload.get("artefacts", []))
        _render_router_debug(payload.get("router_debug"))

    _render_sources(payload.get("citations", []))


def _render_response_meta(payload: dict, telemetry: dict) -> None:
    meta = [payload["role"]]
    if payload.get("state"):
        meta.append(payload["state"])
    if "confidence" in telemetry:
        meta.append(f"confidence={telemetry['confidence']:.2f}")
    st.caption(" · ".join(meta))


def _render_questions(questions: list[dict]) -> None:
    if not questions:
        return

    st.markdown("**Follow-up questions**")
    for question in questions:
        label = question["label"]
        options = question.get("options", [])
        if options:
            st.markdown(f"- {label} ({', '.join(options)})")
        else:
            st.markdown(f"- {label}")


def _render_artefacts(artefacts: list[dict]) -> None:
    if not artefacts:
        return

    with st.expander("Artefacts"):
        for artefact in artefacts:
            st.markdown(f"**{artefact['title']}**")
            st.caption(artefact["type"])
            st.write(artefact["content"])


def _render_sources(citations: list[dict]) -> None:
    with st.expander("Sources"):
        if not citations:
            st.caption("Keine Quellen verfügbar.")
            return

        for i, citation in enumerate(citations, 1):
            title = citation.get("title") or citation["source"]
            locator = citation.get("locator") or "ohne Seitenangabe"
            st.markdown(f"**{i}. {title}**")
            st.caption(f"{citation['source']} · {locator} · chunk {citation['chunk_id']}")


def _render_router_debug(router_debug: dict | None) -> None:
    if not router_debug:
        return

    model_selection = model_selection_for_role(router_debug["role"])
    model_name = router_debug.get("model_name") or model_selection["model_name"]
    model_reason = router_debug.get("model_reason") or model_selection["reason"]

    with st.expander("Router Debug"):
        st.caption(
            " · ".join(
                [
                    router_debug["role"],
                    router_debug["knowledge_mode"],
                    router_debug["distance"],
                    f"confidence={router_debug['routing_confidence']}",
                    "fallback" if router_debug["used_fallback"] else "agent",
                ]
            )
        )
        st.markdown(f"**Reason:** {router_debug['reason']}")
        st.markdown(f"**Model:** `{model_name}`")
        st.markdown(f"**Model reason:** {model_reason}")
        st.markdown(f"**Verification need:** {router_debug['verification_need']}")
        st.markdown(f"**Next state:** {router_debug['next_state']}")

        _render_required_context(router_debug)
        _render_session_context(router_debug)


def _render_required_context(router_debug: dict) -> None:
    required_context = router_debug.get("required_context", [])
    if not required_context:
        return

    st.markdown("**Required context**")
    for item in required_context:
        st.markdown(f"- {item}")


def _render_session_context(router_debug: dict) -> None:
    detected_themes = router_debug.get("detected_themes", [])
    knowledge_gaps = router_debug.get("knowledge_gaps", [])
    related_sessions = router_debug.get("related_sessions", [])
    if not (detected_themes or knowledge_gaps or related_sessions):
        return

    st.markdown("**Session context**")
    if detected_themes:
        st.caption("Themes: " + ", ".join(detected_themes[:8]))
    if knowledge_gaps:
        st.caption("Knowledge gaps: " + ", ".join(knowledge_gaps[:8]))
    for session in related_sessions[:3]:
        title = session.get("title") or "Previous session"
        query = session.get("query") or ""
        st.markdown(f"- **{title}**: {query}")
