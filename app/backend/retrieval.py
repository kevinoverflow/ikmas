from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.rag.retriever import retrieve_and_rerank


@dataclass
class RetrievalBundle:
    docs: list[Any]
    confidence: float
    top1: float
    avg_top3: float
    coverage: float


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _extract_scores(docs: list[Any]) -> list[float]:
    scores: list[float] = []
    for d in docs:
        raw = d.metadata.get("rerank_score", 0.0)
        try:
            scores.append(_clamp01(float(raw)))
        except (TypeError, ValueError):
            scores.append(0.0)
    return scores


def compute_confidence(docs: list[Any], k_expected: int = 5) -> tuple[float, float, float, float]:
    if not docs:
        return 0.0, 0.0, 0.0, 0.0

    scores = _extract_scores(docs)
    top1 = scores[0] if scores else 0.0

    top3 = scores[:3]
    avg_top3 = sum(top3) / len(top3) if top3 else 0.0

    coverage = _clamp01(len(docs) / float(max(1, k_expected)))

    confidence = _clamp01(0.6 * top1 + 0.3 * avg_top3 + 0.1 * coverage)
    return confidence, top1, avg_top3, coverage


def retrieve_bundle(collection_name: str, query: str, k_retrieve: int = 30, k_final: int = 5) -> RetrievalBundle:
    docs = retrieve_and_rerank(collection_name, query, k_retrieve=k_retrieve, k_final=k_final)
    confidence, top1, avg_top3, coverage = compute_confidence(docs, k_expected=k_final)
    return RetrievalBundle(docs=docs, confidence=confidence, top1=top1, avg_top3=avg_top3, coverage=coverage)
