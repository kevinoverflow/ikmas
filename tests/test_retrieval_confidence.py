from types import SimpleNamespace

from app.backend.retrieval import compute_confidence


def _doc(score):
    return SimpleNamespace(metadata={"rerank_score": score})


def test_confidence_formula():
    docs = [_doc(0.9), _doc(0.8), _doc(0.7), _doc(0.6), _doc(0.5)]
    confidence, top1, avg_top3, coverage = compute_confidence(docs, k_expected=5)

    assert round(top1, 2) == 0.90
    assert round(avg_top3, 2) == 0.80
    assert round(coverage, 2) == 1.00
    assert round(confidence, 2) == round(0.6 * 0.9 + 0.3 * 0.8 + 0.1 * 1.0, 2)


def test_confidence_empty_docs():
    confidence, top1, avg_top3, coverage = compute_confidence([], k_expected=5)
    assert (confidence, top1, avg_top3, coverage) == (0.0, 0.0, 0.0, 0.0)
