import pytest

from app.rag import reranker


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload
        self.raise_called = False

    def raise_for_status(self):
        self.raise_called = True

    def json(self):
        return self._payload


def test_rerank_requires_api_key():
    with pytest.raises(RuntimeError, match="Missing API key"):
        reranker.rerank("query", ["passage"], api_key=None)


def test_rerank_posts_expected_payload_and_reads_results(monkeypatch):
    seen = {}
    response = FakeResponse({"results": [{"index": 1, "relevance_score": 0.77}]})

    def fake_post(url, headers, json, timeout):
        seen["url"] = url
        seen["headers"] = headers
        seen["json"] = json
        seen["timeout"] = timeout
        return response

    monkeypatch.setattr(reranker.requests, "post", fake_post)

    result = reranker.rerank(
        query="What is retrieval?",
        passages=["one", "two"],
        top_n=5,
        base_url="https://example.test/v1/",
        api_key="secret",
        model="rerank-model",
        timeout_s=12,
    )

    assert result == [{"index": 1, "relevance_score": 0.77}]
    assert response.raise_called is True
    assert seen["url"] == "https://example.test/v1/rerank"
    assert seen["headers"] == {
        "Authorization": "Bearer secret",
        "Content-Type": "application/json",
    }
    assert seen["json"] == {
        "model": "rerank-model",
        "query": "What is retrieval?",
        "documents": ["one", "two"],
        "top_n": 2,
    }
    assert seen["timeout"] == 12


def test_rerank_accepts_data_fallback_shape(monkeypatch):
    monkeypatch.setattr(
        reranker.requests,
        "post",
        lambda *args, **kwargs: FakeResponse({"data": [{"index": 0, "relevance_score": 0.5}]}),
    )

    result = reranker.rerank("query", ["passage"], api_key="secret")

    assert result == [{"index": 0, "relevance_score": 0.5}]


def test_rerank_rejects_unexpected_response_shape(monkeypatch):
    monkeypatch.setattr(
        reranker.requests,
        "post",
        lambda *args, **kwargs: FakeResponse({"unexpected": []}),
    )

    with pytest.raises(RuntimeError, match="Unexpected rerank response format"):
        reranker.rerank("query", ["passage"], api_key="secret")
