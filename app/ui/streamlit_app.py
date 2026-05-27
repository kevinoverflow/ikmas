import uuid

import streamlit as st

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
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "docs_indexed" not in st.session_state:
    st.session_state.docs_indexed = False

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "show_execution_debug" not in st.session_state:
    st.session_state.show_execution_debug = True

# DEBUG: Session management controls
with st.sidebar:
    st.header("🔧 Session Controls (Debug)")
    st.checkbox(
        "Show execution debug",
        key="show_execution_debug",
        help="Show routing, single/multi-agent mode, task plans, traces, and raw workflow payloads.",
    )
    
    # Display current session info
    st.caption(f"Current session ID:")
    st.code(st.session_state.session_id)
    
    # Session ID input for debugging
    new_session_id = st.text_input("New Session ID:", value="", placeholder="Enter a custom session ID")
    if st.button("Switch to Session", type="secondary"):
        if new_session_id:
            st.session_state.session_id = new_session_id
            st.session_state.chat_history = []
            st.success(f"Switched to session: {new_session_id}")
            st.rerun()
    
    # Reset to new random session
    if st.button("New Random Session", type="secondary"):
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.chat_history = []
        st.success(f"Created new session: {st.session_state.session_id}")
        st.rerun()
    
    # Clear current session history
    if st.button("Clear Session History"):
        st.session_state.chat_history = []
        st.success("Session history cleared")
        st.rerun()
    
    # List all sessions (dropdown)
    st.divider()
    st.header("📋 Session History")
    
    try:
        from app.backend.sqlite_store import get_conn
        import json
        
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT session_id, user_id, timestamp, router_classification 
            FROM session_history 
            ORDER BY timestamp DESC 
            LIMIT 20
        """)
        sessions = cursor.fetchall()
        
        if sessions:
            # Create a dropdown with session IDs
            session_options = {}
            for session in sessions:
                session_id, user_id, timestamp, classification = session
                # Use full session ID as title for clarity
                display_text = session_id
                if user_id:
                    display_text += f" (User: {user_id})"
                session_options[display_text] = session_id
            
            selected_session_text = st.selectbox(
                "Select a session:",
                options=list(session_options.keys()),
                index=0
            )
            
            if st.button("Switch to Selected Session"):
                selected_session_id = session_options[selected_session_text]
                st.session_state.session_id = selected_session_id
                st.session_state.chat_history = []
                st.success(f"Switched to session: {selected_session_id}")
                st.rerun()
                
        else:
            st.caption("No session history found")
            
    except Exception as e:
        st.caption(f"Error reading sessions: {e}")
    
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


def render_workflow(payload):
    trace = payload.get("agent_trace")
    result = payload.get("workflow_result")
    if not trace and not result:
        return

    with st.expander("Agentic Workflow", expanded=True):
        if trace:
            st.caption(
                " · ".join(
                    [
                        f"parent={trace.get('root_agent', 'unknown')}",
                        f"tasks={trace.get('successful_tasks', 0)}/{trace.get('total_tasks', 0)}",
                        f"failed={trace.get('failed_tasks', 0)}",
                    ]
                )
            )
            for node in trace.get("nodes", []):
                status = node.get("status", "unknown")
                task_id = node.get("task_id", "")
                role = node.get("agent_role", "")
                st.markdown(f"- `{status}` `{task_id}` {role}")
                if node.get("error"):
                    st.caption(node["error"])

        if result:
            st.markdown("**Reusable knowledge artifact**")
            if result.get("decisions"):
                st.markdown("Decisions")
                for item in result["decisions"]:
                    st.markdown(f"- {item.get('decision', item)}")
            if result.get("assumptions"):
                st.markdown("Assumptions")
                for item in result["assumptions"]:
                    st.markdown(f"- {item.get('assumption', item)}")
            if result.get("open_issues"):
                st.markdown("Open issues")
                for item in result["open_issues"]:
                    st.markdown(f"- {item.get('issue', item)}")
            if result.get("learning_summaries"):
                st.markdown("Learning summaries")
                for item in result["learning_summaries"]:
                    st.markdown(f"- **{item.get('concept', 'Concept')}**: {item.get('summary', '')}")
            if result.get("flashcards"):
                st.markdown("Flashcards")
                for item in result["flashcards"]:
                    st.markdown(f"- **{item.get('front', 'Front')}**: {item.get('back', '')}")
            if result.get("artefacts"):
                st.markdown("Generated artefacts")
                for item in result["artefacts"]:
                    st.markdown(f"- **{item.get('title', 'Artefact')}** `{item.get('type', '')}`")
            if result.get("reuse_guidance"):
                st.markdown("Reuse guidance")
                for item in result["reuse_guidance"]:
                    st.markdown(f"- {item}")


def render_execution_debug(payload):
    if not st.session_state.get("show_execution_debug", True):
        return

    router_debug = payload.get("router_debug") or {}
    telemetry = payload.get("telemetry") or {}
    task_plan = payload.get("task_plan")
    planning_debug = payload.get("workflow_planning_debug")
    trace = payload.get("agent_trace")
    workflow_result = payload.get("workflow_result")
    is_multi_agent = bool(trace and trace.get("total_tasks", 0) > 0)
    mode = "multi-agent workflow" if is_multi_agent else "single-agent response"

    with st.expander("Execution Debug", expanded=True):
        c1, c2, c3 = st.columns(3)
        c1.metric("Mode", mode)
        c2.metric("Agent", payload.get("role", "unknown"))
        c3.metric("Retrieval", telemetry.get("retrieval_count", 0))

        st.caption(
            " · ".join(
                [
                    f"intent={telemetry.get('intent', 'unknown')}",
                    f"distance={telemetry.get('distance', 'unknown')}",
                    f"confidence={telemetry.get('confidence', 0):.2f}"
                    if isinstance(telemetry.get("confidence"), (int, float))
                    else "confidence=unknown",
                    "fallback" if telemetry.get("fallback_used") else "normal",
                    "repair" if telemetry.get("repair_used") else "no-repair",
                ]
            )
        )

        if router_debug:
            st.markdown("**Router**")
            st.json(router_debug, expanded=False)

        if task_plan:
            st.markdown("**Task plan**")
            st.json(task_plan, expanded=False)
            if not task_plan.get("should_decompose"):
                st.caption("Decision: stay single-agent for this turn.")

        if planning_debug:
            st.markdown("**Planning agents**")
            st.json(planning_debug, expanded=False)

        if trace:
            st.markdown("**Agent trace**")
            st.json(trace, expanded=False)

        if workflow_result:
            st.markdown("**Workflow result**")
            st.json(workflow_result, expanded=False)

        st.markdown("**Payload keys**")
        st.code(", ".join(sorted(payload.keys())))


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
            render_workflow(payload)
            render_artefacts(payload.get("artefacts", []))
            render_execution_debug(payload)
            render_router_debug(payload.get("router_debug"))

        render_sources(payload.get("citations", []))
