import uuid
import json

import streamlit as st

from app.backend.auth import AuthError, authenticate_user, create_user
from app.backend.llm_client import get_client
from app.backend.orchestrator import handle_turn
from app.backend.router_agent import model_selection_for_role
from app.rag.ingest import split_file, split_documents
from app.infrastructure.config import LLM_MODEL_NAME
from app.rag.storage import (
    list_collection_files,
    save_upload,
    get_file_path,
    delete_file
)
from app.rag.vectorstore import add_docs, clear_collection

COLLECTION_ID = "default"

st.set_page_config(page_title="IKMAS", layout="centered")
st.title("Intelligent Knowledge Management Assistance System")


# Session State Init
if "auth_user" not in st.session_state:
    st.session_state.auth_user = None

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "docs_indexed" not in st.session_state:
    st.session_state.docs_indexed = False

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())


def _set_authenticated_user(user) -> None:
    st.session_state.auth_user = {
        "id": user.user_id,
        "name": user.name,
        "email": user.email,
    }
    st.session_state.session_id = str(uuid.uuid4())
    st.session_state.chat_history = []


def _logout() -> None:
    st.session_state.auth_user = None
    st.session_state.session_id = str(uuid.uuid4())
    st.session_state.chat_history = []
    st.rerun()


def _load_session_chat_history(session_id: str, user_id: str) -> list[dict]:
    from app.backend.sqlite_store import get_conn

    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT user_input, llm_json
            FROM turns
            WHERE session_id = ? AND user_id = ?
            ORDER BY created_at, id
            """,
            (session_id, user_id),
        ).fetchall()

    history = []
    for row in rows:
        try:
            payload = json.loads(row["llm_json"])
        except (TypeError, json.JSONDecodeError):
            continue
        history.append({"user": row["user_input"], "payload": payload})
    return history


def render_auth_workflow() -> bool:
    if st.session_state.auth_user:
        return True

    st.subheader("Sign in")
    login_tab, register_tab = st.tabs(["Login", "Create account"])

    with login_tab:
        with st.form("login_form"):
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            submitted = st.form_submit_button("Login", type="primary")

        if submitted:
            user = authenticate_user(email, password)
            if user is None:
                st.error("Invalid email or password.")
            else:
                _set_authenticated_user(user)
                st.success(f"Welcome back, {user.name}.")
                st.rerun()

    with register_tab:
        with st.form("register_form"):
            name = st.text_input("Name", key="register_name")
            email = st.text_input("Email", key="register_email")
            password = st.text_input("Password", type="password", key="register_password")
            confirm_password = st.text_input("Confirm password", type="password", key="register_confirm_password")
            submitted = st.form_submit_button("Create account", type="primary")

        if submitted:
            if password != confirm_password:
                st.error("Passwords do not match.")
            else:
                try:
                    user = create_user(name, email, password)
                except AuthError as e:
                    st.error(str(e))
                else:
                    _set_authenticated_user(user)
                    st.success(f"Account created for {user.name}.")
                    st.rerun()

    st.info("Create an account or log in to use your private IKMAS workspace.")
    return False


if not render_auth_workflow():
    st.stop()

current_user = st.session_state.auth_user

# DEBUG: Session management controls
with st.sidebar:
    st.header("Account")
    st.write(f"**{current_user['name']}**")
    st.caption(current_user["email"])
    st.caption(f"User ID: {current_user['id']}")
    if st.button("Log out", type="secondary"):
        _logout()

    st.divider()
    st.header("Chats")

    if st.button("New chat", type="primary", use_container_width=True):
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.chat_history = []
        st.rerun()

    try:
        from app.backend.sqlite_store import get_conn
        
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT session_id, session_title, user_query, timestamp
            FROM session_history 
            WHERE user_id = ?
            ORDER BY timestamp DESC 
            LIMIT 20
        """, (current_user["id"],))
        sessions = cursor.fetchall()
        
        if sessions:
            for session in sessions:
                session_id, title, user_query, timestamp = session
                display_title = title or user_query or "Untitled chat"
                button_type = "primary" if session_id == st.session_state.session_id else "secondary"
                if st.button(
                    display_title,
                    key=f"chat::{session_id}",
                    type=button_type,
                    use_container_width=True,
                ):
                    st.session_state.session_id = session_id
                    st.session_state.chat_history = _load_session_chat_history(
                        session_id,
                        current_user["id"],
                    )
                    st.rerun()
                
        else:
            st.caption("No chats yet.")
            
    except Exception as e:
        st.caption(f"Error reading chats: {e}")

    with st.expander("Session debug"):
        st.caption("Current session ID:")
        st.code(st.session_state.session_id)

        new_session_id = st.text_input("New Session ID:", value="", placeholder="Enter a custom session ID")
        if st.button("Switch to Session", type="secondary"):
            if new_session_id:
                st.session_state.session_id = new_session_id
                st.session_state.chat_history = _load_session_chat_history(
                    new_session_id,
                    current_user["id"],
                )
                st.success(f"Switched to session: {new_session_id}")
                st.rerun()

        if st.button("Clear Session History"):
            st.session_state.chat_history = []
            st.success("Session history cleared")
            st.rerun()
    
    st.divider()

# Sidebar: Model info
with st.sidebar:
    st.header("Model Information")
    try:
        client = get_client()
        models = client.models.list()
        for m in models.data:
            st.markdown(m.id)
        st.divider()
        st.caption(f"Chat model: {LLM_MODEL_NAME}")
    except Exception as e:
        st.warning(f"Could not list models: {e}")


st.subheader("📁 Dateien (Server / data/uploads)")

files = list_collection_files(COLLECTION_ID, exts=(".pdf", ".docx", ".pptx", ".txt", ".md"))

if not files:
    st.info("Keine Dateien vorhanden.")
else:
    for f in files:
        c1, c2, c3 = st.columns([6, 2, 2])
        with c1:
            st.write(f"**{f.path.name}**  ·  {f.size_bytes} bytes  ·  {f.sha256[:12]}")
        with c2:
            # Download button reads server file bytes
            path = get_file_path(COLLECTION_ID, f.path.name)
            if path:
                # Determine MIME type based on file extension
                mime_type = "application/pdf"
                if f.path.suffix.lower() in [".docx", ".doc"]:
                    mime_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                elif f.path.suffix.lower() in [".pptx", ".ppt"]:
                    mime_type = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
                elif f.path.suffix.lower() == ".txt":
                    mime_type = "text/plain"
                elif f.path.suffix.lower() == ".md":
                    mime_type = "text/markdown"
                elif f.path.suffix.lower() in [".png", ".jpg", ".jpeg", ".webp"]:
                    mime_type = f"image/{f.path.suffix.lower()[1:]}"
                
                st.download_button(
                    "Download",
                    data=path.read_bytes(),
                    file_name=f.path.name,
                    mime=mime_type,
                    key=f"dl::{f.path.name}",
                    use_container_width=True,
                )
        with c3:
            # Delete with confirm pattern
            if st.button("Delete", key=f"del::{f.path.name}", use_container_width=True):
                st.session_state["delete_candidate"] = f.path.name

# Confirm delete (prevents accidental deletes)
candidate = st.session_state.get("delete_candidate")
if candidate:
    st.warning(f"Willst du **{candidate}** wirklich löschen?")
    cc1, cc2 = st.columns([1, 1])
    with cc1:
        if st.button("Ja, löschen", type="primary", use_container_width=True):
            ok = delete_file(COLLECTION_ID, candidate)
            st.session_state["delete_candidate"] = None
            st.toast("Gelöscht" if ok else "Nicht gefunden", icon="🗑️")
            st.rerun()
    with cc2:
        if st.button("Abbrechen", use_container_width=True):
            st.session_state["delete_candidate"] = None
            st.rerun()


st.divider()
st.subheader("⬆️ Neue Dateien hinzufügen")

uploaded_files = st.file_uploader(
    "Dateien auswählen (PDF, DOCX, PPTX, TXT, MD)",
    type=["pdf", "docx", "pptx", "txt", "md"],
    accept_multiple_files=True,
)

name_conflict_mode = st.selectbox("Bei Namenskonflikt:", ["skip", "replace", "rename"], index=0)

if uploaded_files and st.button("Speichern (mit Dedupe)", type="primary"):
    saved = 0
    skipped = 0
    replaced = 0
    renamed = 0

    for uf in uploaded_files:
        status, _ = save_upload(
            collection_id=COLLECTION_ID,
            filename=uf.name,
            data=uf.getvalue(),
            on_name_conflict=name_conflict_mode,
        )
        if status == "saved":
            saved += 1
        elif status == "skipped_identical":
            skipped += 1
        elif status == "replaced":
            replaced += 1
        elif status == "renamed":
            renamed += 1

    st.success(f"saved={saved}, replaced={replaced}, renamed={renamed}, skipped_identical={skipped}")
    st.rerun()


st.divider()
st.subheader("🔎 Index (Chroma) aus serverseitigen Dateien")
reindex = st.checkbox("Reindex (Chroma collection vorher leeren)", value=False)

if st.button("Index now", type="primary", disabled=len(list_collection_files(COLLECTION_ID, exts=(".pdf", ".docx", ".pptx", ".txt", ".md"))) == 0):
    with st.spinner("Chunking + Embedding + Writing to Chroma..."):
        if reindex: 
            clear_collection(COLLECTION_ID)

        docs = []
        for stored in list_collection_files(COLLECTION_ID, exts=(".pdf", ".docx", ".pptx", ".txt", ".md")):
            docs.extend(split_documents(split_file(stored)))

        n = add_docs(COLLECTION_ID, docs)
        st.session_state.docs_indexed = True

    st.success(f"Indexed {n} chunks")

def _format_chat_history_for_backend(chat_history):
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


def ask_assistant(question: str):
    return handle_turn(
        session_id=st.session_state.session_id,
        user_input=question,
        user_id=current_user["id"],
        collection_name=COLLECTION_ID,
        chat_history=_format_chat_history_for_backend(st.session_state.chat_history),
    )


def render_questions(questions):
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


def render_artefacts(artefacts):
    if not artefacts:
        return

    with st.expander("Artefacts"):
        for artefact in artefacts:
            st.markdown(f"**{artefact['title']}**")
            st.caption(artefact["type"])
            st.write(artefact["content"])


def render_sources(citations):
    with st.expander("Sources"):
        if not citations:
            st.caption("Keine Quellen verfügbar.")
            return

        for i, citation in enumerate(citations, 1):
            title = citation.get("title") or citation["source"]
            locator = citation.get("locator") or "ohne Seitenangabe"
            st.markdown(f"**{i}. {title}**")
            st.caption(f"{citation['source']} · {locator} · chunk {citation['chunk_id']}")


def render_router_debug(router_debug):
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

        required_context = router_debug.get("required_context", [])
        if required_context:
            st.markdown("**Required context**")
            for item in required_context:
                st.markdown(f"- {item}")


# Chat
st.markdown("---")
query = st.chat_input(
    "Ask a question about your files:",
)

if query:
    with st.spinner("Thinking..."):
        try:
            payload = ask_assistant(query)
        except Exception as e:
            st.error(f"Error: {e}")
            st.stop()

    st.session_state.chat_history.append(
        {"user": query, "payload": payload}
    )


# Render chat + sources
if st.session_state.chat_history:
    for turn in st.session_state.chat_history:
        st.chat_message("user").markdown(turn["user"])
        payload = turn["payload"]
        telemetry = payload.get("telemetry", {})

        with st.chat_message("assistant"):
            st.markdown(payload["assistant_message"])

            meta = [payload["role"]]
            if payload.get("state"):
                meta.append(payload["state"])
            if "confidence" in telemetry:
                meta.append(f"confidence={telemetry['confidence']:.2f}")
            st.caption(" · ".join(meta))

            render_questions(payload.get("questions", []))
            render_artefacts(payload.get("artefacts", []))
            render_router_debug(payload.get("router_debug"))

        render_sources(payload.get("citations", []))
