from langchain_core.prompts import ChatPromptTemplate
from langchain_openai.embeddings import OpenAIEmbeddings
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
import streamlit as st
import tempfile
from typing import List
from openai import OpenAI
import os
import sys
from getpass import getpass

# LLM SETUP-
SCADS_API_KEY = os.getenv("SCADS_API_KEY")
if not SCADS_API_KEY:
    SCADS_API_KEY = getpass("Enter your SCADS API key: ")
    if not SCADS_API_KEY:
        print("No API key provided, exiting.")
        sys.exit(1)

os.environ["OPENAI_API_KEY"] = SCADS_API_KEY
os.environ["OPENAI_BASE_URL"] = "https://llm.scads.ai/v1"

client = OpenAI(base_url="https://llm.scads.ai/v1", api_key=SCADS_API_KEY)
LANGUAGE_MODEL_NAME = "Qwen/Qwen3-VL-8B-Instruct"

# EMBEDDING MODEL SETUP
EMBEDDING_MODEL = "Qwen/Qwen3-Embedding-4B"
TOP_K = 3


st.set_page_config(page_title="RAG SECI App", layout="centered")
st.title("RAG SECI App")

# get all available models
models = client.models.list()
st.sidebar.header("Model Information")
for model in models.data:
    st.sidebar.markdown(model.id)


if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "retriever" not in st.session_state:
    st.session_state.retriever = None

if "docs_indexed" not in st.session_state:
    st.session_state.docs_indexed = False

# Upload PDFs
uploaded_files = st.file_uploader(
    "Upload one or more PDF files",
    type=["pdf"],
    accept_multiple_files=True
)

# Load & split PDFs


@st.cache_data
def load_and_split_pdfs(files) -> List:
    docs = []

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=400,
        chunk_overlap=50,
        add_start_index=True,
    )

    for file in files:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            temp_file.write(file.read())
            temp_file_path = temp_file.name

        loader = PyPDFLoader(temp_file_path)
        loaded_docs = loader.load()

        for doc in loaded_docs:
            split_docs = text_splitter.split_documents([doc])
            docs.extend(split_docs)
    return docs


# Build retriever
@st.cache_resource
def build_retriever(docs):
    embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)

    vectorstore = InMemoryVectorStore.from_documents(
        documents=docs,
        embedding=embeddings,
    )

    return vectorstore.as_retriever(
        search_kwargs={"k": TOP_K}
    )


# Build vector store on upload
if uploaded_files and not st.session_state.docs_indexed:
    with st.spinner("Processing PDFs..."):
        documents = load_and_split_pdfs(uploaded_files)
        st.session_state.retriever = build_retriever(documents)
        st.session_state.docs_indexed = True

    st.success(f"Indexed {len(documents)} document chunks")


def format_docs(docs):
    return "\n\n".join(d.page_content for d in docs)


SYSTEM_RULES = """You are a helpful assistant.

You may use:
- Context (retrieved from the PDFs) for document questions
- Chat History for questions about what the user/assistant previously said or asked

Rules:
- If the user asks about the PDFs/paper, use the Context as the source of truth.
- If the user asks about the conversation (e.g., "What was my last question?"), use the Chat History.
- If you cannot find the answer in either Context or Chat History, say you don't know.
"""


def format_chat_history(chat_history):
    messages = []
    for chat in chat_history:
        messages.append({"role": "user", "content": chat["user"]})
        messages.append({"role": "assistant", "content": chat["bot"]})
    return messages


def get_openai_rag_chain(query: str):
    # Retrieve docs
    docs = st.session_state.retriever.invoke(query)
    context = format_docs(docs)

    # Build messages properly (System + History + User)
    messages = [{"role": "system", "content": SYSTEM_RULES}]
    messages += format_chat_history(st.session_state.chat_history)

    # User message: question + context (klar getrennt)
    user_content = f"""Context:
        {context}

        Question:
        {query}
"""
    messages.append({"role": "user", "content": user_content})

    response = client.chat.completions.create(
        model=LANGUAGE_MODEL_NAME,
        messages=messages,
    )

    return response.choices[0].message.content, docs


query = st.chat_input(
    "Ask a question about your PDFs:",
    disabled=st.session_state.retriever is None,
)


def send_query(query: str):
    with st.spinner("Thinking..."):
        response, retrieved_docs = get_openai_rag_chain(query)

    st.session_state.chat_history.append({
        "user": query,
        "bot": response,
        "sources": retrieved_docs,
    })


if query:
    send_query(query)


if st.session_state.chat_history:
    st.markdown("---")

    for chat in st.session_state.chat_history:
        st.chat_message("user").markdown(chat["user"])
        st.chat_message("ai").markdown(chat["bot"])

        with st.expander("Sources"):
            for i, doc in enumerate(chat["sources"], 1):
                page = doc.metadata.get("page", "N/A")
                source = doc.metadata.get("source", "Uploaded PDF")
                st.markdown(f"**{i}. {source} (page {page})**")
                st.caption(doc.page_content[:300] + "…")
