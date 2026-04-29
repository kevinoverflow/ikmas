from typing import List, Tuple, Literal
from pathlib import Path
import logging

from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from app.rag.tokenizer import get_tokenizer
from app.rag.storage import save_upload, StoredFile
from app.rag.extractors.pdf_extractor import extract_pdf_documents
from app.rag.extractors.text_extractor import extract_text_documents
from app.rag.extractors.markdown_extractor import extract_markdown_documents
from app.rag.extractors.image_extractor import extract_image_documents
from app.infrastructure.tracing import traceable

logger = logging.getLogger(__name__)

ConflictAction = Literal["skip", "replace", "rename"]
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

@traceable
def split_file(stored: StoredFile, chunk_size: int = 512, chunk_overlap: int = 80) -> List[Document]:
    """
    Main entry point for splitting files into documents based on file type.
    
    Args:
        stored: StoredFile object to process
        chunk_size: Size of chunks for splitting
        chunk_overlap: Overlapx between chunks
        
    Returns:
        List of Document objects ready for chunking
    """
    # Determine file type and route accordingly
    suffix = Path(stored.original_name).suffix.lower()
    
    # Initialize docs list
    docs = []
    
    if suffix == ".pdf":
        docs = extract_pdf_documents(stored)
    elif suffix == ".txt":
        docs = extract_text_documents(stored)
    elif suffix == ".md":
        docs = split_markdown_documents(extract_markdown_documents(stored))
    elif suffix in [".png", ".jpg", ".jpeg", ".webp"]:
        docs = extract_image_documents(stored)
    else:
        raise ValueError(f"Unsupported file type: {suffix}")
    
    # Add common metadata to all docs
    for doc in docs:
        doc.metadata.update({
            "file_id": stored.file_id,
            "source": stored.original_name,
        })
    
    return docs

@traceable
def split_documents(docs: List[Document], chunk_size: int = 512, chunk_overlap: int = 80) -> List[Document]:
    """
    Split documents into chunks using RecursiveCharacterTextSplitter.
    
    Args:
        docs: List of Document objects to split
        chunk_size: Size of chunks for splitting
        chunk_overlap: Overlap between chunks
        
    Returns:
        List of chunked Document objects
    """
    if not docs:
        return []

    tokenizer = get_tokenizer()
    
    splitter = RecursiveCharacterTextSplitter.from_huggingface_tokenizer(
        tokenizer,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        add_start_index=True
    )

    return splitter.split_documents(docs)

@traceable
def ingest_uploads(
        collection_id: str, 
        uploaded_files,
        on_name_conflict: ConflictAction = "skip",
        chunk_size: int = 512,
        chunk_overlap: int = 80,
        ) -> Tuple[List[Document], dict]:
    """
    Takes Streamlit UploadedFile objects, persists them, returns:
      - all_chunks: list of split LangChain Documents
      - stats: counts of saved/skipped/replaced/renamed/errors

    Behavior:
    - Identical content (hash match in collection) => skipped_identical
    - Same filename, different content => controlled by on_name_conflict
    """
    all_chunks = []
    stats = {
        "saved": 0,
        "replaced": 0,
        "renamed": 0,
        "skipped_identical": 0,
        "skipped_conflict": 0,
        "errors": 0,
        "error_messages": [],
    }
    
    for f in uploaded_files:
        try:
            # Save the upload
            status, stored = save_upload(
                collection_id=collection_id,
                filename=f.name,
                data=f.getvalue(),
                on_name_conflict=on_name_conflict
            )

            if status in stats:
                stats[status] += 1
            else: 
                stats["saved"] += 1

            if stored is None:
                continue
            
            # Process the file according to its type
            docs = split_file(stored, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
            
            # Split into chunks
            chunks = split_documents(docs, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
            
            all_chunks.extend(chunks)

        except Exception as e:
            stats["errors"] += 1
            stats["error_messages"].append(f"{getattr(f, 'name', '<unknown>')}: {e}")
            # don't crash whole ingest; caller can surface errors if desired
            continue

    return all_chunks, stats
                                
