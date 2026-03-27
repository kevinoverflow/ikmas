import sys
import types
from pathlib import Path

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


class FakeDocument:
    def __init__(self, page_content: str, metadata: dict | None = None):
        self.page_content = page_content
        self.metadata = metadata or {}


def test_uploads_to_bytes_reads_each_upload():
    uploads = [FakeUpload("a.pdf", b"aaa"), FakeUpload("b.pdf", b"bbb")]

    assert ingest.uploads_to_bytes(uploads) == [
        ("a.pdf", b"aaa"),
        ("b.pdf", b"bbb"),
    ]


def test_split_pdf_file_adds_storage_metadata_before_splitting(monkeypatch, tmp_path):
    seen = {}
    docs = [FakeDocument("page one"), FakeDocument("page two", {"page": 2})]

    class FakeSplitter:
        def split_documents(self, split_docs):
            seen["split_docs"] = split_docs
            return ["chunk-a", "chunk-b"]

    class FakeTextSplitter:
        @staticmethod
        def from_huggingface_tokenizer(tokenizer, chunk_size, chunk_overlap, add_start_index):
            seen["tokenizer"] = tokenizer
            seen["chunk_size"] = chunk_size
            seen["chunk_overlap"] = chunk_overlap
            seen["add_start_index"] = add_start_index
            return FakeSplitter()

    class FakeLoader:
        def __init__(self, path):
            seen["path"] = path

        def load(self):
            return docs

    tokenizer = object()
    stored = StoredFile(
        file_id="file-123",
        path=tmp_path / "doc.pdf",
        original_name="source.pdf",
        size_bytes=42,
        sha256="abc",
    )

    monkeypatch.setattr(ingest, "get_tokenizer", lambda: tokenizer)
    monkeypatch.setattr(ingest, "RecursiveCharacterTextSplitter", FakeTextSplitter)
    monkeypatch.setattr(ingest, "PyPDFLoader", FakeLoader)

    chunks = ingest.split_pdf_file(stored, chunk_size=256, chunk_overlap=32)

    assert chunks == ["chunk-a", "chunk-b"]
    assert seen["tokenizer"] is tokenizer
    assert seen["chunk_size"] == 256
    assert seen["chunk_overlap"] == 32
    assert seen["add_start_index"] is True
    assert seen["path"] == str(Path(tmp_path / "doc.pdf"))
    assert docs[0].metadata == {"file_id": "file-123", "source": "source.pdf"}
    assert docs[1].metadata == {"page": 2, "file_id": "file-123", "source": "source.pdf"}
    assert seen["split_docs"] == docs


def test_ingest_uploads_uses_getvalue_and_collects_chunks(monkeypatch):
    def fake_save_upload(collection_id, filename, data, on_name_conflict):
        assert data == b"pdf-bytes"

        class Stored:
            file_id = "id"
            original_name = filename
            path = "dummy.pdf"

        return "saved", Stored()

    monkeypatch.setattr(ingest, "save_upload", fake_save_upload)
    monkeypatch.setattr(ingest, "split_pdf_file", lambda stored, chunk_size, chunk_overlap: ["chunk1", "chunk2"])

    chunks, stats = ingest.ingest_uploads("default", [FakeUpload("a.pdf", b"pdf-bytes")])

    assert chunks == ["chunk1", "chunk2"]
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
