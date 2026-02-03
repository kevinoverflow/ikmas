import streamlit as st
from pathlib import Path
from typing import Dict, List

from app.rag.ingest import split_pdf_file
from app.rag.retriever import build_inmemory_retriever
from app.rag.llm import get_client
from app.rag.prompts import SYSTEM_RULES, wrap_user_message
from app.infrastructure.config import LANGUAGE_MODEL_NAME
from app.rag.storage import (
    list_collection_files,
    save_upload,
    get_file_path,
    delete_file
)

COLLECTION_ID = "default"

st.set_page_config(page_title="IKMAS", layout="centered")
st.title("Intelligent Knowledge Management Assistance System")


# Session State Init
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "retriever" not in st.session_state:
    st.session_state.retriever = None

if "docs_indexed" not in st.session_state:
    st.session_state.docs_indexed = False

if "pending" not in st.session_state:
    # list of dicts: {"safe_name","orig_name","data","sha","conflict"}
    st.session_state.pending = None

if "decisions" not in st.session_state:
    # safe_name -> "skip"/"replace"/"rename"
    st.session_state.decisions = {}


# Sidebar: Model info
with st.sidebar:
    st.header("Model Information")
    try:
        client = get_client()
        models = client.models.list()
        for m in models.data:
            st.markdown(m.id)
        st.divider()
        st.caption(f"Chat model: {LANGUAGE_MODEL_NAME}")
    except Exception as e:
        st.warning(f"Could not list models: {e}")


st.subheader("📁 Dateien (Server / data/uploads)")

files = list_collection_files(COLLECTION_ID)

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
                st.download_button(
                    "Download",
                    data=path.read_bytes(),
                    file_name=f.path.name,
                    mime="application/pdf",
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
st.subheader("⬆️ Neue PDFs hinzufügen")

uploaded_files = st.file_uploader(
    "PDFs auswählen",
    type=["pdf"],
    accept_multiple_files=True,
)

if uploaded_files and st.button("Speichern (mit Dedupe)", type="primary"):
    # simple policy for now:
    # identical => skip, name-conflict => ask globally (or per file, if you prefer)
    name_conflict_mode = st.selectbox("Bei Namenskonflikt:", ["skip", "replace", "rename"], index=0)

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
st.subheader("🔎 Index (InMemory) aus serverseitigen Dateien")

if st.button("Index now", type="primary", disabled=len(list_collection_files(COLLECTION_ID)) == 0):
    docs = []
    for stored in list_collection_files(COLLECTION_ID):
        docs.extend(split_pdf_file(stored))
    st.session_state.retriever = build_inmemory_retriever(docs)
    st.session_state.docs_indexed = True
    st.success(f"Indexed {len(docs)} chunks")


# Helpers (UI-only)
def _format_docs(docs) -> str:
    return "\n\n".join(d.page_content for d in docs)


def _format_chat_history_for_messages(chat_history):
    messages = []
    for turn in chat_history:
        messages.append({"role": "user", "content": turn["user"]})
        messages.append({"role": "assistant", "content": turn["bot"]})
    return messages


def ask_rag(question: str):
    if st.session_state.retriever is None:
        raise RuntimeError("Retriever not initialized. Please index PDFs first.")

    docs = st.session_state.retriever.invoke(question)
    context = _format_docs(docs)

    messages = [{"role": "system", "content": SYSTEM_RULES}]
    messages += _format_chat_history_for_messages(st.session_state.chat_history)
    messages.append({"role": "user", "content": wrap_user_message(context=context, question=question)})

    client = get_client()
    resp = client.chat.completions.create(
        model=LANGUAGE_MODEL_NAME,
        messages=messages,
    )
    return resp.choices[0].message.content, docs


# Chat
st.markdown("---")
query = st.chat_input(
    "Ask a question about your PDFs:",
    disabled=st.session_state.retriever is None,
)

if query:
    with st.spinner("Thinking..."):
        try:
            response, retrieved_docs = ask_rag(query)
        except Exception as e:
            st.error(f"Error: {e}")
            st.stop()

    st.session_state.chat_history.append(
        {"user": query, "bot": response, "sources": retrieved_docs}
    )


# Render chat + sources
if st.session_state.chat_history:
    for turn in st.session_state.chat_history:
        st.chat_message("user").markdown(turn["user"])
        st.chat_message("ai").markdown(turn["bot"])

        with st.expander("Sources"):
            for i, doc in enumerate(turn["sources"], 1):
                page = doc.metadata.get("page", "N/A")
                source = doc.metadata.get("source", "Uploaded PDF")
                st.markdown(f"**{i}. {source} (page {page})**")
                st.caption(doc.page_content[:300] + "…")
