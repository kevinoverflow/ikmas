#!/usr/bin/env python3
"""
Debug script for testing ingestion pipeline components.
This script processes a file through the ingestion pipeline and outputs results
without storing anything to the database or vector store.
"""

from pathlib import Path
import sys
from typing import List

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.rag.storage import StoredFile
from app.rag.ingest import split_file, split_documents
from app.rag.tokenizer import get_tokenizer
from langchain_core.documents import Document

def debug_ingestion(file_path: str):
    """Process a file through the ingestion pipeline and display results."""
    
    # Create a mock StoredFile object
    file_path = Path(file_path)
    if not file_path.exists():
        print(f"Error: File {file_path} does not exist")
        return
    
    stored = StoredFile(
        file_id="debug-test-" + file_path.name,
        path=file_path,
        original_name=file_path.name,
        size_bytes=file_path.stat().st_size,
        sha256="debug-hash-placeholder"
    )
    
    print(f"Processing file: {file_path}")
    print(f"File size: {file_path.stat().st_size} bytes")
    print("-" * 50)
    
    # Step 1: Split file into documents
    try:
        documents = split_file(stored, chunk_size=512, chunk_overlap=80)
        print(f"Generated {len(documents)} documents:")
        
        for i, doc in enumerate(documents):
            print(f"\nDocument {i+1}:")
            print(f"  Type: {doc.metadata.get('chunk_type', 'unknown')}")
            print(f"  Source: {doc.metadata.get('source', 'unknown')}")
            print(f"  Content preview: {doc.page_content[:100]}{'...' if len(doc.page_content) > 100 else ''}")
            print(f"  Metadata: {doc.metadata}")
            
    except Exception as e:
        print(f"Error in split_file: {e}")
        return
    
    # Step 2: Split documents into chunks
    try:
        if documents:
            chunks = split_documents(documents, chunk_size=512, chunk_overlap=80)
            print(f"\nSplit into {len(chunks)} chunks:")
            
            for i, chunk in enumerate(chunks[:3]):  # Show first 3 chunks
                print(f"\nChunk {i+1}:")
                print(f"  Content preview: {chunk.page_content[:100]}{'...' if len(chunk.page_content) > 100 else ''}")
                print(f"  Metadata: {chunk.metadata}")
                
            if len(chunks) > 3:
                print(f"... and {len(chunks) - 3} more chunks")
        else:
            print("No documents to split into chunks")
            
    except Exception as e:
        print(f"Error in split_documents: {e}")

def main():
    """Main function to run the debug ingestion."""
    if len(sys.argv) != 2:
        print("Usage: python scripts/debug_ingestion.py <file_path>")
        print("Example: python scripts/debug_ingestion.py test.pdf")
        return
    
    file_path = sys.argv[1]
    debug_ingestion(file_path)

if __name__ == "__main__":
    main()
