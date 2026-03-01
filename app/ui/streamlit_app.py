from __future__ import annotations

import json
import uuid
from pathlib import Path

import streamlit as st

from app.backend.orchestrator import handle_turn
from app.backend.sqlite_store import init_db
from app.rag.ingest import split_file
from app.rag.storage import delete_file, get_file_path, list_collection_files, save_upload
from app.rag.vectorstore import add_docs, clear_collection

COLLECTION_ID = "default"

MIME_BY_SUFFIX = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".md": "text/markdown",
    ".txt": "text/plain",
}

st.set_page_config(page_title="IKMAS", layout="centered")
st.title("Intelligent Knowledge Management Assistance System")

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "delete_candidate" not in st.session_state:
    st.session_state.delete_candidate = None

init_db()

with st.sidebar:
    st.subheader("Interaktionsmodus")
    role_mode = st.radio("Rollenwahl", ["Automatisch", "Manuell"], index=0)
    manual_role = None
    if role_mode == "Manuell":
        manual_role = st.selectbox(
            "Rolle",
            ["DigitalMemoryAgent", "MentorAgent", "TutoringAgent", "ConceptMiningAgent"],
            index=1,
        )

st.caption(f"Session: {st.session_state.session_id[:8]}")
st.subheader("Dateien (Server / data/uploads)")
files = list_collection_files(COLLECTION_ID)

if not files:
    st.info("Keine Dateien vorhanden.")
else:
    for f in files:
        c1, c2, c3 = st.columns([6, 2, 2])
        with c1:
            st.write(f"**{f.path.name}**  ·  {f.size_bytes} bytes  ·  {f.sha256[:12]}")
        with c2:
            path = get_file_path(COLLECTION_ID, f.path.name)
            if path:
                st.download_button(
                    "Download",
                    data=path.read_bytes(),
                    file_name=f.path.name,
                    mime=MIME_BY_SUFFIX.get(Path(f.path.name).suffix.lower(), "application/octet-stream"),
                    key=f"dl::{f.path.name}",
                    use_container_width=True,
                )
        with c3:
            if st.button("Delete", key=f"del::{f.path.name}", use_container_width=True):
                st.session_state.delete_candidate = f.path.name

candidate = st.session_state.delete_candidate
if candidate:
    st.warning(f"Willst du **{candidate}** wirklich löschen?")
    cc1, cc2 = st.columns([1, 1])
    with cc1:
        if st.button("Ja, löschen", type="primary", use_container_width=True):
            ok = delete_file(COLLECTION_ID, candidate)
            st.session_state.delete_candidate = None
            st.toast("Gelöscht" if ok else "Nicht gefunden", icon="🗑️")
            st.rerun()
    with cc2:
        if st.button("Abbrechen", use_container_width=True):
            st.session_state.delete_candidate = None
            st.rerun()

st.divider()
st.subheader("Neue Dateien hinzufügen")

uploaded_files = st.file_uploader(
    "Dateien auswählen",
    type=["pdf", "docx", "md", "txt"],
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
st.subheader("Index (Chroma) aus serverseitigen Dateien")
reindex = st.checkbox("Reindex (Chroma collection vorher leeren)", value=False)

if st.button("Index now", type="primary", disabled=len(list_collection_files(COLLECTION_ID)) == 0):
    with st.spinner("Chunking + Embedding + Writing to Chroma..."):
        if reindex:
            clear_collection(COLLECTION_ID)

        docs = []
        for stored in list_collection_files(COLLECTION_ID):
            docs.extend(split_file(stored, project=COLLECTION_ID, artefact_type="source_document"))

        n = add_docs(COLLECTION_ID, docs)

    st.success(f"Indexed {n} chunks")


def _render_turn(turn: dict) -> None:
    payload = turn["payload"]

    st.chat_message("user").markdown(turn["user"])
    st.chat_message("assistant").markdown(payload.get("assistant_message", ""))

    role = payload.get("role")
    state = payload.get("state")
    confidence = payload.get("telemetry", {}).get("confidence")
    phase = payload.get("interaction_phase")
    mode = payload.get("mode")
    st.caption(f"Mode: {mode} | Phase: {phase} | Role: {role} | State: {state} | Confidence: {confidence}")

    questions = payload.get("questions", [])
    if questions:
        with st.expander("Rückfragen"):
            for q in questions:
                st.markdown(f"- **{q.get('prompt', 'Question')}** ({q.get('type', 'text')})")
                opts = q.get("options", [])
                if opts:
                    st.caption("Optionen: " + ", ".join(opts))

    artefacts = payload.get("artefacts", [])
    if artefacts:
        with st.expander("Artefakte"):
            for a in artefacts:
                st.markdown(f"### {a.get('title', 'Untitled')} ({a.get('type', 'summary')})")
                st.markdown(a.get("body_md", ""))

    citations = payload.get("citations", [])
    if citations:
        with st.expander("Quellen"):
            for c in citations:
                st.markdown(f"- `{c.get('source_id', 'unknown')}` (score={c.get('score', 0.0):.2f})")


st.markdown("---")
query = st.chat_input("Frage zu deinen Dokumenten oder antworte auf Rückfragen")

if query:
    with st.spinner("Thinking..."):
        try:
            payload = handle_turn(
                session_id=st.session_state.session_id,
                user_input=query,
                user_id="streamlit_user",
                role_override=manual_role,
            )
        except Exception as e:
            st.error(f"Error: {e}")
            st.stop()

    st.session_state.chat_history.append({"user": query, "payload": payload})
    st.rerun()

if st.session_state.chat_history:
    for turn in st.session_state.chat_history:
        _render_turn(turn)

# Role-gate structured answers.
if st.session_state.chat_history:
    last_payload = st.session_state.chat_history[-1]["payload"]
    last_questions = last_payload.get("questions", [])
    if last_questions:
        st.markdown("---")
        is_role_gate_question = any(str(q.get("id", "")).startswith("rg_") for q in last_questions)
        st.subheader("Rückfragen beantworten")
        with st.form("followup_answers_form"):
            answers = {}
            for q in last_questions:
                qid = q.get("id", "q")
                qtype = q.get("type", "single_choice")
                prompt = q.get("prompt", qid)
                opts = q.get("options", [])

                if qtype == "single_choice" and opts:
                    answers[qid] = st.radio(prompt, opts, key=f"ans::{qid}")
                elif qtype == "multi_choice" and opts:
                    answers[qid] = st.multiselect(prompt, opts, key=f"ans::{qid}")
                else:
                    answers[qid] = st.text_input(prompt, key=f"ans::{qid}")

            custom_question = st.text_input(
                "Eigene Rückfrage (optional)",
                key="ans::custom_question",
                placeholder="Optional: freie Ergänzung",
            )
            submitted = st.form_submit_button("Antworten senden")

        if submitted:
            structured_payload = {"role_gate_answers": answers} if is_role_gate_question else {"answers": answers}
            if custom_question.strip():
                structured_payload["custom_question"] = custom_question.strip()
            structured_input = json.dumps(structured_payload, ensure_ascii=True)

            with st.spinner("Thinking..."):
                payload = handle_turn(
                    session_id=st.session_state.session_id,
                    user_input=structured_input,
                    user_id="streamlit_user",
                    role_override=manual_role,
                )

            st.session_state.chat_history.append({"user": structured_input, "payload": payload})
            st.rerun()
