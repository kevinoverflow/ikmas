"""Text file extractor for IKMAS ingestion system."""

from typing import List
from langchain_core.documents import Document
from app.rag.storage import StoredFile


def extract_text_documents(stored: StoredFile) -> List[Document]:
    """
    Extract documents from a text file.
    
    Args:
        stored: StoredFile object containing the text file
        
    Returns:
        List of Document objects with metadata
    """
    # Read the file content
    with open(stored.path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Create a single document with metadata
    doc = Document(
        page_content=content,
        metadata={
            "file_id": stored.file_id,
            "source": stored.original_name,
            "chunk_type": "plain_text"
        }
    )
    
    return [doc]