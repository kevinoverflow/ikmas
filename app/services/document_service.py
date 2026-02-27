from __future__ import annotations

from typing import Dict, List, Tuple
from uuid import uuid4

from app.infrastructure.db import db_cursor
from app.rag.ingest import split_pdf_file
from app.rag.storage import delete_file, list_collection_files, save_upload, sha256_bytes
from app.rag.vectorstore import add_docs, clear_collection
from app.services.project_service import ProjectService


class DocumentService:
    def __init__(self, project_service: ProjectService):
        self.project_service = project_service

    def upload_files(
        self,
        project_id: str,
        files: List[Tuple[str, bytes]],
        on_name_conflict: str = "skip",
    ) -> Dict[str, int]:
        project = self.project_service.get_project(project_id)
        collection_id = project["collection_id"]
        stats = {
            "saved": 0,
            "replaced": 0,
            "renamed": 0,
            "skipped_identical": 0,
            "skipped_conflict": 0,
        }
        for filename, data in files:
            status, stored = save_upload(
                collection_id=collection_id,
                filename=filename,
                data=data,
                on_name_conflict=on_name_conflict,
            )
            stats[status] = stats.get(status, 0) + 1
            if not stored:
                continue
            with db_cursor() as cur:
                file_hash = sha256_bytes(data)
                cur.execute(
                    """
                    INSERT INTO documents (id, project_id, filename, filetype, size_bytes, sha256, status, chunk_count)
                    VALUES (?, ?, ?, ?, ?, ?, 'uploaded', 0)
                    ON CONFLICT(project_id, filename)
                    DO UPDATE SET
                        size_bytes = excluded.size_bytes,
                        sha256 = excluded.sha256,
                        status = 'uploaded'
                    """,
                    (
                        str(uuid4()),
                        project_id,
                        stored.path.name,
                        stored.path.suffix.lower().lstrip(".") or "pdf",
                        len(data),
                        file_hash,
                    ),
                )
        return stats

    def list_documents(self, project_id: str) -> List[Dict[str, object]]:
        self.project_service.get_project(project_id)
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT id, project_id, filename, filetype, size_bytes, sha256, uploaded_at, status, chunk_count
                FROM documents
                WHERE project_id = ?
                ORDER BY uploaded_at DESC
                """,
                (project_id,),
            )
            rows = cur.fetchall()
        return [dict(r) for r in rows]

    def delete_document(self, doc_id: str) -> bool:
        with db_cursor() as cur:
            cur.execute("SELECT id, project_id, filename FROM documents WHERE id = ?", (doc_id,))
            row = cur.fetchone()
            if not row:
                return False
            project = self.project_service.get_project(row["project_id"])
            deleted = delete_file(project["collection_id"], row["filename"])
            cur.execute("DELETE FROM document_chunks WHERE document_id = ?", (doc_id,))
            cur.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        return deleted

    def rebuild_index(self, project_id: str, reindex: bool = False) -> int:
        project = self.project_service.get_project(project_id)
        collection_id = project["collection_id"]
        if reindex:
            clear_collection(collection_id)
        files = list_collection_files(collection_id)
        docs = []
        with db_cursor() as cur:
            for stored in files:
                split_docs = split_pdf_file(stored)
                cur.execute(
                    """
                    SELECT id, uploaded_at
                    FROM documents
                    WHERE project_id = ? AND filename = ?
                    LIMIT 1
                    """,
                    (project_id, stored.path.name),
                )
                row = cur.fetchone()
                if not row:
                    doc_id = str(uuid4())
                    cur.execute(
                        """
                        INSERT INTO documents (id, project_id, filename, filetype, size_bytes, sha256, status, chunk_count)
                        VALUES (?, ?, ?, ?, ?, ?, 'indexed', ?)
                        """,
                        (
                            doc_id,
                            project_id,
                            stored.path.name,
                            stored.path.suffix.lower().lstrip(".") or "pdf",
                            stored.size_bytes,
                            stored.sha256,
                            len(split_docs),
                        ),
                    )
                else:
                    doc_id = row["id"]
                    uploaded_at = row["uploaded_at"]
                    cur.execute(
                        """
                        UPDATE documents
                        SET status = 'indexed', chunk_count = ?
                        WHERE id = ?
                        """,
                        (len(split_docs), doc_id),
                    )
                if row is None:
                    uploaded_at = None
                cur.execute("DELETE FROM document_chunks WHERE document_id = ?", (doc_id,))
                for idx, d in enumerate(split_docs):
                    chunk_id = f"{doc_id}:{idx}"
                    d.metadata["doc_id"] = doc_id
                    d.metadata["chunk_id"] = chunk_id
                    d.metadata["filetype"] = stored.path.suffix.lower().lstrip(".") or "pdf"
                    if uploaded_at:
                        d.metadata["uploaded_at"] = uploaded_at
                    cur.execute(
                        """
                        INSERT INTO document_chunks (document_id, chunk_index, chunk_id, page, token_count)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (doc_id, idx, chunk_id, d.metadata.get("page"), len(d.page_content.split())),
                    )
                    docs.append(d)
        return add_docs(collection_id, docs) if docs else 0
