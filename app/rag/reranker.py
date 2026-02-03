from typing import List, Dict, Any
import os
import requests

from app.infrastructure.config import BASE_URL, API_KEY, RERANK_MODEL

def rerank(
        query: str,
        passages: List[str],
        top_n: int = 5,
        base_url: str = BASE_URL,
        api_key: str = API_KEY,
        model: str = RERANK_MODEL,
        timeout_s: int = 60,
) -> List[Dict[str, Any]]:
    """
    Calls an OpenAI-compatible rerank endpoint (commonly /v1/rerank).
    Returns a list of dicts with at least {index, relevance_score}.
    """
    if not api_key:
        raise RuntimeError("Missing API key (SCADS_API_KEY / OPENAI_API_KEY).")

    url = base_url.rstrip("/") + "/rerank"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    payload = {
        "model": model,
        "query": query,
        "documents": passages,
        "top_n": min(top_n, len(passages)),
    }

    r = requests.post(url, headers=headers, json=payload, timeout=timeout_s)
    r.raise_for_status()
    data = r.json()

    # Common shapes:
    # { "results": [{"index": 0, "relevance_score": 0.87}, ...] }
    if "results" in data and isinstance(data["results"], list):
        return data["results"]

    # Fallback: some APIs return {"data": [...]}
    if "data" in data and isinstance(data["data"], list):
        return data["data"]

    raise RuntimeError(f"Unexpected rerank response format: keys={list(data.keys())}")