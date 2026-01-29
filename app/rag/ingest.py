import os
import tempfile
from typing import List, Tuple

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader

from app.rag.tokenizer import get_tokenizer

def uploads_to_bytes(files) -> List[Tuple[str, bytes]]:
    return [(f.name, f.getvalue()) for f in files]

def load_and_split_pdfs(files_as_bytes: List[Tuple[str, bytes]], chunk_size=512, chunk_overlap=80):
    tokenizer = get_tokenizer()

    splitter = RecursiveCharacterTextSplitter.from_huggingface_tokenizer(
        tokenizer,
        chunk_size = chunk_size,
        chunk_overlap = chunk_overlap,
        add_start_index=True
    )

    all_docs = []
    for filename, data in files_as_bytes:
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(data)
                temp_path = tmp.name

            docs = PyPDFLoader(temp_path).load()
            for d in docs:
                d.metadata["source"] = filename

            all_docs.extend(splitter.split_documents(docs))
        finally:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)

    return all_docs