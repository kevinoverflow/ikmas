from __future__ import annotations

from statistics import mean
from typing import Any

from langchain_core.documents import Document

from app.rag.retriever import retrieve_and_rerank


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def normalize_score(score: float | None) -> float:
    if score is None:
        return 0.0
    return clamp01(float(score))


def extract_score(doc: Document) -> float:
    metadata = getattr(doc, "metadata", {}) or {}
    raw_score = metadata.get("rerank_score", 0.0)
    return normalize_score(raw_score)


def compute_coverage(scores: list[float], threshold: float = 0.5, k: int = 5) -> float:
    topk = scores[:k]
    if not topk:
        return 0.0

    hits = sum(1 for s in topk if s >= threshold)
    return hits / len(topk)


def compute_confidence(scores: list[float]) -> tuple[float, float, float, float]:
    if not scores:
        return 0.0, 0.0, 0.0, 0.0

    scores = [normalize_score(s) for s in scores]

    top1 = scores[0]
    avg_top3 = mean(scores[:3]) if len(scores) >= 3 else mean(scores)
    coverage = compute_coverage(scores)

    confidence = clamp01(0.6 * top1 + 0.3 * avg_top3 + 0.1 * coverage)

    return top1, avg_top3, coverage, confidence


def document_to_chunk(doc: Document, score: float) -> dict[str, Any]:
    metadata = getattr(doc, "metadata", {}) or {}

    return {
        "chunk_id": str(
            metadata.get("chunk_id")
            or metadata.get("id")
            or metadata.get("source")
            or "unknown"
        ),
        "text": doc.page_content,
        "source": metadata.get("source", "unknown"),
        "title": metadata.get("title"),
        "page": metadata.get("page"),
        "score": score,
        "metadata": metadata,
    }


def run_retrieval(
    query: str,
    collection_name: str,
    k_retrieve: int = 30,
    k_final: int = 8,
) -> dict[str, Any]:
    ranked_docs = retrieve_and_rerank(
        collection_name=collection_name,
        query=query,
        k_retrieve=k_retrieve,
        k_final=k_final,
    )

    if not ranked_docs:
        return {
            "chunks": [],
            "top1": 0.0,
            "avg_top3": 0.0,
            "coverage": 0.0,
            "confidence": 0.0,
        }

    scores = [extract_score(doc) for doc in ranked_docs]
    top1, avg_top3, coverage, confidence = compute_confidence(scores)

    chunks = [
        document_to_chunk(doc=doc, score=score)
        for doc, score in zip(ranked_docs, scores, strict=False)
    ]

    return {
        "chunks": chunks,
        "top1": top1,
        "avg_top3": avg_top3,
        "coverage": coverage,
        "confidence": confidence,
    }