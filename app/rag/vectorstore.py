from __future__ import annotations
import json
from typing import Any, List

from langchain_openai.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

from app.infrastructure.config import CHROMA_DIR, EMBEDDING_MODEL, BASE_URL, API_KEY

MetadataValue = str | int | float | bool | List[str] | List[int] | List[float] | List[bool]

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
    vs.add_documents(sanitize_documents_for_chroma(docs))
    vs.persist()
    return len(docs)

def similarity_search(collection_name: str, query: str, k: int):
    vs = get_chroma(collection_name)
    return vs.similarity_search(query, k=k)


def _is_chroma_scalar(value: Any) -> bool:
    return isinstance(value, (str, int, float, bool))


def _is_chroma_list(value: list) -> bool:
    if not value:
        return False

    return all(_is_chroma_scalar(item) for item in value)


def _coerce_metadata_value(value: Any) -> MetadataValue | None:
    if value is None:
        return None

    if _is_chroma_scalar(value):
        return value

    if isinstance(value, list):
        if _is_chroma_list(value):
            return value
        if not value:
            return None

    return json.dumps(value, ensure_ascii=True)


def sanitize_metadata(metadata: dict) -> dict:
    """
    Keep metadata compatible with Chroma's strict insert validation.

    Chroma accepts scalar metadata values and non-empty lists of scalar values.
    Empty lists and nested structures are useful inside the app, but must be
    dropped or serialized before upsert.
    """
    sanitized = {}

    for key, value in metadata.items():
        coerced = _coerce_metadata_value(value)
        if coerced is not None:
            sanitized[key] = coerced

    return sanitized


def sanitize_documents_for_chroma(docs: List[Document]) -> List[Document]:
    return [
        Document(page_content=doc.page_content, metadata=sanitize_metadata(doc.metadata))
        for doc in docs
    ]


def clear_collection(collection_name: str) -> None:
    """
    Clears all docs in a collection (simple & safe).
    """
    vs = get_chroma(collection_name)
    # Get all document IDs and delete them
    all_ids = vs._collection.get()["ids"]
    if all_ids:
        vs._collection.delete(ids=all_ids)
    vs.persist()
