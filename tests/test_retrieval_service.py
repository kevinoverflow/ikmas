from langchain_core.documents import Document

from app.domain.types import ChatFilters
from app.services import retrieval_service as retrieval_module
from app.services.retrieval_service import RetrievalService


def test_retrieval_service_passes_mmr_flag(monkeypatch):
    captured = {}

    def fake_retrieve_and_rerank(collection_name, query, k_retrieve, k_final, use_mmr):
        captured["use_mmr"] = use_mmr
        return [Document(page_content="x", metadata={"filetype": "pdf"})]

    monkeypatch.setattr(retrieval_module, "retrieve_and_rerank", fake_retrieve_and_rerank)

    svc = RetrievalService()
    docs = svc.retrieve("default", "q", policy={"k": 8, "mmr": False}, filters=ChatFilters(k=3, mmr=True))
    assert captured["use_mmr"] is True
    assert len(docs) == 1


def test_retrieval_service_applies_doctype_filter(monkeypatch):
    def fake_retrieve_and_rerank(collection_name, query, k_retrieve, k_final, use_mmr):
        return [
            Document(page_content="a", metadata={"filetype": "pdf"}),
            Document(page_content="b", metadata={"filetype": "txt"}),
        ]

    monkeypatch.setattr(retrieval_module, "retrieve_and_rerank", fake_retrieve_and_rerank)
    svc = RetrievalService()
    docs = svc.retrieve("default", "q", policy={"k": 8, "mmr": False}, filters=ChatFilters(k=5, doctype=["pdf"]))
    assert len(docs) == 1
    assert docs[0].metadata["filetype"] == "pdf"


def test_retrieval_service_handles_naive_uploaded_at(monkeypatch):
    def fake_retrieve_and_rerank(collection_name, query, k_retrieve, k_final, use_mmr):
        return [
            Document(page_content="fresh", metadata={"filetype": "pdf", "uploaded_at": "2099-01-01T00:00:00"}),
            Document(page_content="old", metadata={"filetype": "pdf", "uploaded_at": "2000-01-01T00:00:00"}),
        ]

    monkeypatch.setattr(retrieval_module, "retrieve_and_rerank", fake_retrieve_and_rerank)
    svc = RetrievalService()
    docs = svc.retrieve(
        "default",
        "q",
        policy={"k": 8, "mmr": False, "date_range_days": 30},
        filters=ChatFilters(k=5),
    )
    assert len(docs) == 1
    assert docs[0].page_content == "fresh"
