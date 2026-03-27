from app.rag import retriever


class FakeDoc:
    def __init__(self, page_content: str, metadata: dict | None = None):
        self.page_content = page_content
        self.metadata = metadata or {}


def test_build_inmemory_retriever_uses_project_embedding_config(monkeypatch):
    seen = {}

    class FakeEmbeddings:
        def __init__(self, **kwargs):
            seen["embedding_kwargs"] = kwargs

    class FakeVectorStore:
        @classmethod
        def from_documents(cls, docs, embedding):
            seen["docs"] = docs
            seen["embedding"] = embedding
            return cls()

        def as_retriever(self, search_kwargs):
            seen["search_kwargs"] = search_kwargs
            return "retriever-object"

    monkeypatch.setattr(retriever, "OpenAIEmbeddings", FakeEmbeddings)
    monkeypatch.setattr(retriever, "InMemoryVectorStore", FakeVectorStore)
    monkeypatch.setattr(retriever, "EMBEDDING_MODEL", "embed-model")
    monkeypatch.setattr(retriever, "API_KEY", "secret")
    monkeypatch.setattr(retriever, "BASE_URL", "https://example.test/v1")
    monkeypatch.setattr(retriever, "TOP_K", 7)

    result = retriever.build_inmemory_retriever(["doc-1", "doc-2"])

    assert result == "retriever-object"
    assert seen["docs"] == ["doc-1", "doc-2"]
    assert seen["search_kwargs"] == {"k": 7}
    assert seen["embedding_kwargs"] == {
        "model": "embed-model",
        "api_key": "secret",
        "base_url": "https://example.test/v1",
        "check_embedding_ctx_length": False,
    }


def test_retrieve_and_rerank_returns_empty_without_docs(monkeypatch):
    monkeypatch.setattr(retriever, "retrieve", lambda *args, **kwargs: [])

    result = retriever.retrieve_and_rerank("default", "What is RAG?")

    assert result == []


def test_retrieve_and_rerank_orders_valid_results_and_attaches_scores(monkeypatch):
    docs = [
        FakeDoc("first", {"chunk_id": "c1"}),
        FakeDoc("second", {"chunk_id": "c2"}),
        FakeDoc("third", {"chunk_id": "c3"}),
    ]

    seen = {}

    def fake_retrieve(collection_name, query, k):
        seen["retrieve_args"] = (collection_name, query, k)
        return docs

    def fake_rerank(query, passages, top_n):
        seen["rerank_args"] = (query, passages, top_n)
        return [
            {"index": 2, "relevance_score": 0.91},
            {"index": None, "relevance_score": 0.99},
            {"index": -1, "relevance_score": 0.5},
            {"index": 7, "relevance_score": 0.4},
            {"index": "1", "relevance_score": 0.88},
        ]

    monkeypatch.setattr(retriever, "retrieve", fake_retrieve)
    monkeypatch.setattr(retriever, "rerank", fake_rerank)

    result = retriever.retrieve_and_rerank("default", "Explain embeddings", k_retrieve=11, k_final=2)

    assert seen["retrieve_args"] == ("default", "Explain embeddings", 11)
    assert seen["rerank_args"] == ("Explain embeddings", ["first", "second", "third"], 2)
    assert result == [docs[2], docs[1]]
    assert docs[2].metadata["rerank_score"] == 0.91
    assert docs[1].metadata["rerank_score"] == 0.88
    assert "rerank_score" not in docs[0].metadata
