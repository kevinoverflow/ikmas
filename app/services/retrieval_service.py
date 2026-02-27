from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from typing import Dict, List

from app.domain.types import ChatFilters
from app.infrastructure.db import db_cursor
from app.rag.retriever import retrieve_and_rerank


class RetrievalService:
    def _merge_policy_and_filters(self, policy: Dict[str, object], filters: ChatFilters) -> Dict[str, object]:
        merged = {
            "k": int(policy.get("k", 5)),
            "mmr": bool(policy.get("mmr", False)),
            "date_range_days": policy.get("date_range_days"),
            "doctype": policy.get("doctype"),
            "rerank_strategy": str(policy.get("rerank_strategy", "balanced")),
        }
        # User-provided filters can narrow scope, never broaden policy k.
        merged["k"] = min(int(filters.k), int(merged["k"])) if filters.k else int(merged["k"])
        if filters.mmr:
            merged["mmr"] = True
        if filters.date_range_days:
            pol_days = merged.get("date_range_days")
            merged["date_range_days"] = (
                min(int(pol_days), int(filters.date_range_days))
                if pol_days
                else int(filters.date_range_days)
            )
        if filters.doctype:
            merged["doctype"] = filters.doctype
        return merged

    def retrieve(self, collection_id: str, query: str, policy: Dict[str, object], filters: ChatFilters) -> List[dict]:
        effective = self._merge_policy_and_filters(policy, filters)
        k = int(effective["k"])
        k_retrieve = max(k * 6, 20)
        raw_docs = retrieve_and_rerank(
            collection_id,
            query,
            k_retrieve=k_retrieve,
            k_final=k_retrieve,
            use_mmr=bool(effective["mmr"]),
        )

        filtered = []
        for doc in raw_docs:
            metadata = doc.metadata or {}
            if effective["doctype"]:
                filetype = str(metadata.get("filetype", "")).lower()
                if filetype not in {d.lower() for d in effective["doctype"]}:
                    continue
            if effective["date_range_days"]:
                uploaded_at = metadata.get("uploaded_at")
                if uploaded_at:
                    try:
                        ts = datetime.fromisoformat(str(uploaded_at).replace("Z", "+00:00"))
                        if ts.tzinfo is None:
                            ts = ts.replace(tzinfo=timezone.utc)
                        cutoff = datetime.now(timezone.utc) - timedelta(days=int(effective["date_range_days"]))
                        if ts < cutoff:
                            continue
                    except ValueError:
                        pass
            filtered.append(doc)
            if len(filtered) >= k:
                break
        return filtered

    def log_retrieval(self, project_id: str, mode: str, query: str, filters: ChatFilters, policy_applied: Dict[str, object]) -> None:
        try:
            with db_cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO retrieval_logs (project_id, mode, query, k, mmr, filters_json)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        project_id,
                        mode,
                        query,
                        filters.k,
                        1 if filters.mmr else 0,
                        json.dumps(
                            {
                                "date_range_days": filters.date_range_days,
                                "doctype": filters.doctype,
                                "policy_applied": policy_applied,
                            }
                        ),
                    ),
                )
        except Exception:
            # Logging should not break serving path.
            return

    def log_chat_output(
        self,
        project_id: str,
        mode: str,
        query: str,
        schema_ok: bool,
        response_json: str,
        citation_count: int,
        confidence: float,
        citation_coverage: float,
    ) -> None:
        try:
            with db_cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO chat_outputs (project_id, mode, query, schema_ok, response_json, citation_count, confidence, citation_coverage)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        project_id,
                        mode,
                        query,
                        1 if schema_ok else 0,
                        response_json,
                        citation_count,
                        confidence,
                        citation_coverage,
                    ),
                )
        except Exception:
            # Logging should not break serving path.
            return

    def log_interaction(
        self,
        project_id: str,
        user_id: str,
        message: str,
        mode_override: str,
        inferred_mode: str,
        router_role: str,
        seci_state: str,
        router_confidence: float,
        strict_citations: bool,
        retrieval_k: int,
        citations_used: int,
        latency_ms: int,
    ) -> None:
        try:
            with db_cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO interaction_log (
                        project_id, user_id, message, mode_override, inferred_mode, router_role, seci_state,
                        router_confidence, strict_citations, retrieval_k, citations_used, latency_ms
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        project_id,
                        user_id,
                        message,
                        mode_override,
                        inferred_mode,
                        router_role,
                        seci_state,
                        router_confidence,
                        1 if strict_citations else 0,
                        retrieval_k,
                        citations_used,
                        latency_ms,
                    ),
                )
        except Exception:
            return
