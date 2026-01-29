import streamlit as st

from app.rag.ingest import uploads_to_bytes, load_and_split_pdfs
from app.rag.retriever import build_inmemory_retriever
from app.rag.llm import get_client
from app.rag.prompts import SYSTEM_RULES, wrap_user_message
from app.infrastructure.config import LANGUAGE_MODEL_NAME


st.set_page_config(page_title="RAG SECI App", layout="centered")
st.title("RAG SECI App")


# Session State Init
if "chat_history" not in st.session_state:
    # list of dicts: {"user": str, "bot": str, "sources": List[Document]}
    st.session_state.chat_history = []

if "retriever" not in st.session_state:
    st.session_state.retriever = None

if "docs_indexed" not in st.session_state:
    st.session_state.docs_indexed = False


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


# Upload PDFs
uploaded_files = st.file_uploader(
    "Upload one or more PDF files",
    type=["pdf"],
    accept_multiple_files=True,
)

col_a, col_b = st.columns([1, 1])
with col_a:
    index_btn = st.button(
        "Index PDFs",
        type="primary",
        disabled=not uploaded_files,
        use_container_width=True,
    )

with col_b:
    reset_btn = st.button(
        "Reset Session",
        disabled=not (st.session_state.docs_indexed or st.session_state.chat_history),
        use_container_width=True,
    )

if reset_btn:
    st.session_state.chat_history = []
    st.session_state.retriever = None
    st.session_state.docs_indexed = False
    st.rerun()

if index_btn and uploaded_files:
    with st.spinner("Processing PDFs..."):
        files_as_bytes = uploads_to_bytes(uploaded_files)
        documents = load_and_split_pdfs(files_as_bytes)
        st.session_state.retriever = build_inmemory_retriever(documents)
        st.session_state.docs_indexed = True
    st.success(f"Indexed {len(documents)} document chunks")


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
    """Retrieval + Prompt build + LLM call. Returns (answer, retrieved_docs)."""
    if st.session_state.retriever is None:
        raise RuntimeError("Retriever not initialized. Please index PDFs first.")

    # 1) retrieve
    docs = st.session_state.retriever.invoke(question)
    context = _format_docs(docs)

    # 2) build messages
    messages = [{"role": "system", "content": SYSTEM_RULES}]
    messages += _format_chat_history_for_messages(st.session_state.chat_history)
    messages.append({"role": "user", "content": wrap_user_message(context=context, question=question)})

    # 3) call model
    client = get_client()
    resp = client.chat.completions.create(
        model=LANGUAGE_MODEL_NAME,
        messages=messages,
    )
    answer = resp.choices[0].message.content
    return answer, docs


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
