from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from app.domain.types import RetrievalResult
from app.infrastructure.config import LANGUAGE_MODEL_NAME
from app.rag.ingest import split_pdf_file
from app.rag.llm import get_client
from app.rag.prompts import SYSTEM_RULES, wrap_user_message
from app.rag.retriever import retrieve_and_rerank
from app.rag.storage import list_collection_files, save_upload
from app.rag.vectorstore import add_docs, clear_collection
from app.services.contracts import KnowledgeServiceContract


class KnowledgeService(KnowledgeServiceContract):
    def upload_files(
        self, collection_id: str, files: List[Tuple[str, bytes]], on_name_conflict: str = "skip"
    ) -> Dict[str, int]:
        stats = {
            "saved": 0,
            "replaced": 0,
            "renamed": 0,
            "skipped_identical": 0,
            "skipped_conflict": 0,
        }
        for filename, data in files:
            status, _ = save_upload(
                collection_id=collection_id,
                filename=filename,
                data=data,
                on_name_conflict=on_name_conflict,
            )
            stats[status] = stats.get(status, 0) + 1
        return stats

    def rebuild_index(self, collection_id: str, reindex: bool = False) -> int:
        if reindex:
            clear_collection(collection_id)
        docs = []
        for stored in list_collection_files(collection_id):
            docs.extend(split_pdf_file(stored))
        return add_docs(collection_id, docs) if docs else 0

    def query(
        self,
        collection_id: str,
        question: str,
        chat_history: Optional[List[Dict[str, str]]] = None,
        k_retrieve: int = 30,
        k_final: int = 5,
    ) -> RetrievalResult:
        docs = retrieve_and_rerank(collection_id, question, k_retrieve=k_retrieve, k_final=k_final)
        context = "\n\n".join(d.page_content for d in docs)

        messages = [{"role": "system", "content": SYSTEM_RULES}]
        for turn in chat_history or []:
            user_text = turn.get("user")
            bot_text = turn.get("bot")
            if user_text:
                messages.append({"role": "user", "content": user_text})
            if bot_text:
                messages.append({"role": "assistant", "content": bot_text})
        messages.append({"role": "user", "content": wrap_user_message(context=context, question=question)})

        client = get_client()
        resp = client.chat.completions.create(model=LANGUAGE_MODEL_NAME, messages=messages)
        answer = resp.choices[0].message.content

        scores = [float(d.metadata.get("rerank_score", 0.0) or 0.0) for d in docs]
        confidence = max(scores) if scores else 0.0
        confidence = min(max(confidence, 0.0), 1.0)

        sources = []
        for d in docs:
            sources.append(
                {
                    "source": d.metadata.get("source", "Uploaded PDF"),
                    "page": d.metadata.get("page"),
                    "rerank_score": d.metadata.get("rerank_score"),
                    "content": d.page_content,
                }
            )

        return RetrievalResult(
            answer=answer,
            sources=sources,
            confidence=confidence,
            retrieved_count=len(docs),
        )
