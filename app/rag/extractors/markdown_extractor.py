"""Markdown extractor for IKMAS ingestion system."""

from typing import List
from langchain_text_splitters import MarkdownHeaderTextSplitter
from langchain_core.documents import Document
from app.rag.storage import StoredFile

MARKDOWN_HEADERS_TO_SPLIT_ON = [
    ("#", "Header 1"),
    ("##", "Header 2"),
    ("###", "Header 3"),
    ("####", "Header 4"),
    ("#####", "Header 5"),
    ("######", "Header 6"),
]


def split_markdown_documents(docs: List[Document]) -> List[Document]:
    """
    Split raw markdown documents by header structure before token chunking.
    """
    if not docs:
        return []

    splitter = MarkdownHeaderTextSplitter(headers_to_split_on=MARKDOWN_HEADERS_TO_SPLIT_ON)
    split_docs: List[Document] = []

    for source_doc in docs:
        section_docs = splitter.split_text(source_doc.page_content)
        if not section_docs:
            split_docs.append(source_doc)
            continue

        for section_doc in section_docs:
            metadata = source_doc.metadata.copy()
            metadata.update(section_doc.metadata)
            metadata["chunk_type"] = "markdown_section"
            split_docs.append(Document(page_content=section_doc.page_content, metadata=metadata))

    return split_docs


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
