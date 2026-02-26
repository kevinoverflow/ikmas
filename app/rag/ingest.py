from typing import List, Tuple, Literal

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader

from app.rag.tokenizer import get_tokenizer
from app.rag.storage import save_upload, StoredFile

ConflictAction = Literal["skip", "replace", "rename"]

def uploads_to_bytes(files) -> List[Tuple[str, bytes]]:
    return [(f.name, f.getvalue()) for f in files]

def split_pdf_file(stored: StoredFile, chunk_size=512, chunk_overlap=80):
    tokenizer = get_tokenizer()

    splitter = RecursiveCharacterTextSplitter.from_huggingface_tokenizer(
        tokenizer,
        chunk_size = chunk_size,
        chunk_overlap = chunk_overlap,
        add_start_index=True
    )

    docs = PyPDFLoader(str(stored.path)).load()

    for d in docs:
        d.metadata.update({
            "file_id": stored.file_id,
            "source": stored.original_name,
        })

    return splitter.split_documents(docs)

def ingest_uploads(
        collection_id: str, 
        uploaded_files,
        on_name_conflict: ConflictAction = "skip",
        chunk_size: int = 512,
        chunk_overlap: int = 80,
        ) -> Tuple[List, dict]:
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
            data = f.getvalue()
            status, stored = save_upload(
            collection_id=collection_id,
            filename=f.name,
            data=data,
            on_name_conflict=on_name_conflict
            )

            if status in stats:
                stats[status] += 1
            else: 
                stats["saved"] += 1

            if stored is None:
                continue

            chunks = split_pdf_file(
                stored,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
            all_chunks.extend(chunks)

            
        except Exception as e:
            stats["errors"] += 1
            stats["error_messages"].append(f"{getattr(f, 'name', '<unknown>')}: {e}")
            # don't crash whole ingest; caller can surface errors if desired
            continue

    return all_chunks, stats
                                
