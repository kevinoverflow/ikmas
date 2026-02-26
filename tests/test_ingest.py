import sys
import types

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


class FakeUpload:
    def __init__(self, name: str, data: bytes):
        self.name = name
        self._data = data

    def getvalue(self):
        return self._data


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
