from __future__ import annotations
import os
from typing import List

from chromadb.config import Settings
from langchain_openai.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma

from app.infrastructure.config import CHROMA_DIR, EMBEDDING_MODEL, BASE_URL, API_KEY

def get_chroma(collection_name: str) -> Chroma:
    if not API_KEY:
        raise RuntimeError("Missing API key (SCADS_API_KEY / OPENAI_API_KEY).")

    # Guard against leaked legacy keys from shell/session that can break chromadb settings.
    for key in list(os.environ.keys()):
        if key.startswith("CHROMA_") or key.startswith("chroma_"):
            os.environ.pop(key, None)

    embeddings = OpenAIEmbeddings(
        model = EMBEDDING_MODEL,
        api_key=API_KEY,
        base_url=BASE_URL,
        check_embedding_ctx_length=False
    )

    settings = Settings(
        anonymized_telemetry=False,
        is_persistent=True,
        persist_directory=str(CHROMA_DIR),
    )

    try:
        return Chroma(
            collection_name=collection_name,
            persist_directory=str(CHROMA_DIR),
            client_settings=settings,
            embedding_function=embeddings,
        )
    except Exception as exc:
        # Compatibility fallback for certain chromadb/langchain version combos.
        if "unable to infer type for attribute" not in str(exc):
            raise
        import chromadb

        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        return Chroma(
            collection_name=collection_name,
            client=client,
            embedding_function=embeddings,
        )

def retrieve(collection_name: str, query: str, k: int):
    vs = get_chroma(collection_name)
    return vs.similarity_search(query, k=k)


def retrieve_mmr(collection_name: str, query: str, k: int, fetch_k: int | None = None):
    vs = get_chroma(collection_name)
    try:
        return vs.max_marginal_relevance_search(query, k=k, fetch_k=fetch_k or max(k * 4, 20))
    except Exception:
        # Fallback for vectorstore backends that don't expose MMR consistently.
        return vs.similarity_search(query, k=k)

def add_docs(collection_name: str, docs: List) -> int:
    vs = get_chroma(collection_name)
    vs.add_documents(docs)
    vs.persist()
    return len(docs)

def similarity_search(collection_name: str, query: str, k: int):
    vs = get_chroma(collection_name)
    return vs.similarity_search(query, k=k)

def clear_collection(collection_name: str) -> None:
    """
    Clears all docs in a collection (simple & safe).
    """
    vs = get_chroma(collection_name)
    # langchain Chroma exposes underlying collection; delete all
    vs._collection.delete(where={})
    vs.persist()
