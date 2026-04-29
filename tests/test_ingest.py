import sys
import types
from pathlib import Path

from langchain_core.documents import Document

# Stub transformers before importing ingest -> tokenizer
transformers_stub = types.ModuleType("transformers")


class _DummyAutoTokenizer:
    @staticmethod
    def from_pretrained(*args, **kwargs):
        class _Tok:
            def encode(self, text, add_special_tokens=False):
                return text.split()

        return _Tok()


transformers_stub.AutoTokenizer = _DummyAutoTokenizer
sys.modules.setdefault("transformers", transformers_stub)

from app.rag import ingest
from app.rag.storage import StoredFile


class FakeUpload:
    def __init__(self, name: str, data: bytes):
        self.name = name
        self._data = data

    def getvalue(self):
        return self._data


def _stored_file(name: str) -> StoredFile:
    return StoredFile(
        file_id="file-123",
        path=Path("/tmp") / name,
        original_name=name,
        size_bytes=42,
        sha256="abc",
    )


def test_split_file_routes_image_files_once(monkeypatch):
    stored = _stored_file("diagram.png")
    seen = {"calls": 0}

    def fake_extract_image_documents(arg):
        seen["calls"] += 1
        assert arg is stored
        return [Document(page_content="ocr text", metadata={"chunk_type": "ocr_text"})]

    monkeypatch.setattr(ingest, "extract_image_documents", fake_extract_image_documents)

    docs = ingest.split_file(stored)

    assert seen["calls"] == 1
    assert len(docs) == 1
    assert docs[0].metadata["file_id"] == "file-123"
    assert docs[0].metadata["source"] == "diagram.png"


def test_split_file_routes_markdown_through_ingest_splitter(monkeypatch):
    stored = _stored_file("notes.md")
    raw_docs = [Document(page_content="# Title\n\ncontent", metadata={"chunk_type": "markdown_section"})]
    split_docs = [Document(page_content="content", metadata={"chunk_type": "markdown_section", "Header 1": "Title"})]
    seen = {}

    monkeypatch.setattr(ingest, "extract_markdown_documents", lambda arg: raw_docs)

    def fake_split_markdown_documents(arg):
        seen["split_docs"] = arg
        return split_docs

    monkeypatch.setattr(ingest, "split_markdown_documents", fake_split_markdown_documents)

    docs = ingest.split_file(stored)

    assert seen["split_docs"] == raw_docs
    assert len(docs) == 1
    assert docs[0].page_content == "content"
    assert docs[0].metadata["Header 1"] == "Title"
    assert docs[0].metadata["file_id"] == "file-123"
    assert docs[0].metadata["source"] == "notes.md"


def test_split_markdown_documents_preserves_source_metadata():
    source_doc = Document(
        page_content="# Title\n\nBody text\n\n## Details\n\nMore text",
        metadata={"file_id": "id-1", "source": "notes.md", "chunk_type": "markdown_section"},
    )

    docs = ingest.split_markdown_documents([source_doc])

    assert len(docs) == 2
    assert docs[0].metadata["file_id"] == "id-1"
    assert docs[0].metadata["source"] == "notes.md"
    assert docs[0].metadata["chunk_type"] == "markdown_section"
    assert docs[0].metadata["Header 1"] == "Title"
    assert docs[1].metadata["Header 1"] == "Title"
    assert docs[1].metadata["Header 2"] == "Details"


def test_split_documents_returns_empty_list(monkeypatch):
    tokenizer = object()

    class FakeTextSplitter:
        @staticmethod
        def from_huggingface_tokenizer(tokenizer, chunk_size, chunk_overlap, add_start_index):
            raise AssertionError("splitter should not be constructed for empty input")

    monkeypatch.setattr(ingest, "get_tokenizer", lambda: tokenizer)
    monkeypatch.setattr(ingest, "RecursiveCharacterTextSplitter", FakeTextSplitter)

    assert ingest.split_documents([]) == []


def test_split_documents_uses_splitter(monkeypatch):
    source_doc = Document(page_content="hello world", metadata={"file_id": "id-1", "source": "a.txt"})
    seen = {}

    class FakeSplitter:
        def split_documents(self, split_docs):
            seen["split_docs"] = split_docs
            return [Document(page_content="hello", metadata=split_docs[0].metadata.copy())]

    class FakeTextSplitter:
        @staticmethod
        def from_huggingface_tokenizer(tokenizer, chunk_size, chunk_overlap, add_start_index):
            seen["tokenizer"] = tokenizer
            seen["chunk_size"] = chunk_size
            seen["chunk_overlap"] = chunk_overlap
            seen["add_start_index"] = add_start_index
            return FakeSplitter()

    tokenizer = object()
    monkeypatch.setattr(ingest, "get_tokenizer", lambda: tokenizer)
    monkeypatch.setattr(ingest, "RecursiveCharacterTextSplitter", FakeTextSplitter)

    chunks = ingest.split_documents([source_doc], chunk_size=256, chunk_overlap=32)

    assert len(chunks) == 1
    assert seen["split_docs"] == [source_doc]
    assert seen["tokenizer"] is tokenizer
    assert seen["chunk_size"] == 256
    assert seen["chunk_overlap"] == 32
    assert seen["add_start_index"] is True
    assert chunks[0].metadata["file_id"] == "id-1"
    assert chunks[0].metadata["source"] == "a.txt"


def test_ingest_uploads_uses_split_file_then_split_documents(monkeypatch):
    stored = _stored_file("a.png")

    def fake_save_upload(collection_id, filename, data, on_name_conflict):
        assert collection_id == "default"
        assert filename == "a.png"
        assert data == b"image-bytes"
        return "saved", stored

    source_docs = [Document(page_content="raw image doc", metadata={"chunk_type": "ocr_text"})]
    chunk_docs = [Document(page_content="chunked doc", metadata={"chunk_type": "ocr_text"})]

    monkeypatch.setattr(ingest, "save_upload", fake_save_upload)
    monkeypatch.setattr(ingest, "split_file", lambda arg, chunk_size, chunk_overlap: source_docs)
    monkeypatch.setattr(ingest, "split_documents", lambda docs, chunk_size, chunk_overlap: chunk_docs)

    chunks, stats = ingest.ingest_uploads("default", [FakeUpload("a.png", b"image-bytes")])

    assert chunks == chunk_docs
    assert stats["saved"] == 1
    assert stats["errors"] == 0
    assert stats["error_messages"] == []


def test_ingest_uploads_collects_error_messages(monkeypatch):
    def raising_save_upload(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(ingest, "save_upload", raising_save_upload)

    chunks, stats = ingest.ingest_uploads("default", [FakeUpload("bad.pdf", b"x")])

    assert chunks == []
    assert stats["errors"] == 1
    assert len(stats["error_messages"]) == 1
    assert "bad.pdf" in stats["error_messages"][0]
    assert "boom" in stats["error_messages"][0]
