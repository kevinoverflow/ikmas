"""Markdown extractor for IKMAS ingestion system."""

from typing import List
from langchain_core.documents import Document
from app.rag.storage import StoredFile


def extract_markdown_documents(stored: StoredFile) -> List[Document]:
    """
    Extract raw markdown content as LangChain documents.

    Structural splitting is handled in app.rag.ingest so extractors remain
    focused on reading file content only.
    """
    # Read the file content
    with open(stored.path, 'r', encoding='utf-8') as f:
        content = f.read()

    return [
        Document(
            page_content=content,
            metadata={
                "file_id": stored.file_id,
                "source": stored.original_name,
                "chunk_type": "markdown_section",
            },
        )
    ]
