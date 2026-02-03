from __future__ import annotations
from typing import List

from langchain_openai.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma

from app.infrastructure.config import CHROMA_DIR, EMBEDDING_MODEL, BASE_URL, API_KEY

def get_chroma(collection_name: str) -> Chroma:
    embeddings = OpenAIEmbeddings(
        model = EMBEDDING_MODEL,
        api_key=API_KEY,
        base_url=BASE_URL,
        check_embedding_ctx_length=False
    )

    return Chroma(
        collection_name=collection_name,
        persist_directory=str(CHROMA_DIR),
        embedding_function=embeddings
    )

def retrieve(collection_name: str, query: str, k: int):
    vs = get_chroma(collection_name)
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