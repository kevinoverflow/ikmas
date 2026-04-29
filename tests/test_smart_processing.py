"""Tests for image extractor orchestration."""

import sys
import types
from pathlib import Path
from unittest.mock import patch

# Stub transformers to avoid import issues
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

from app.domain.types import ImageTextResult
from app.rag.extractors.image_extractor import extract_image_documents, should_run_vision, smart_image_processing
from app.rag.ocr import is_text_valid
from app.rag.storage import StoredFile


def _stored_file(name: str = "test-image.png") -> StoredFile:
    return StoredFile(
        file_id="test-file-id",
        path=Path("/fake/path") / name,
        original_name=name,
        size_bytes=1024,
        sha256="test-sha256-hash",
    )


def test_text_validation():
    """Test text validation logic."""
    assert is_text_valid("This is a valid sentence with enough words")
    assert not is_text_valid("Short")
    assert not is_text_valid("12345")
    assert not is_text_valid("")
    assert not is_text_valid("   ")


def test_should_run_vision_for_invalid_ocr():
    stored = _stored_file()
    ocr_result = ImageTextResult(
        text="",
        chunk_type="ocr_text",
        processor="ocr",
        confidence=0.0,
        metadata={},
    )

    assert should_run_vision(stored, ocr_result) is True


def test_extract_image_documents_returns_ocr_only_for_valid_text():
    stored = _stored_file("notes.png")
    ocr_result = ImageTextResult(
        text="This is a valid OCR result with enough words.",
        chunk_type="ocr_text",
        processor="ocr",
        confidence=0.92,
        metadata={"ocr_engine": "tesseract"},
    )

    with patch("app.rag.extractors.image_extractor.run_tesseract_ocr", return_value=ocr_result):
        with patch("app.rag.extractors.image_extractor.run_vision") as mock_run_vision:
            docs = extract_image_documents(stored)

    assert len(docs) == 1
    assert docs[0].metadata["chunk_type"] == "ocr_text"
    assert docs[0].metadata["media_type"] == "image"
    mock_run_vision.assert_not_called()


def test_extract_image_documents_adds_vision_for_visual_filename():
    stored = _stored_file("architecture-diagram.png")
    ocr_result = ImageTextResult(
        text="This is a valid OCR result with enough words.",
        chunk_type="ocr_text",
        processor="ocr",
        confidence=0.92,
        metadata={"ocr_engine": "tesseract"},
    )
    vision_result = ImageTextResult(
        text="A system diagram connecting three services.",
        chunk_type="image_description",
        processor="vision",
        confidence=0.9,
        metadata={"vision_model": "Qwen3-VL-8B-Instruct"},
    )

    with patch("app.rag.extractors.image_extractor.run_tesseract_ocr", return_value=ocr_result):
        with patch("app.rag.extractors.image_extractor.run_vision", return_value=vision_result):
            docs = extract_image_documents(stored)

    assert len(docs) == 2
    assert docs[0].metadata["chunk_type"] == "ocr_text"
    assert docs[1].metadata["chunk_type"] == "image_description"


def test_extract_image_documents_uses_vision_fallback_for_invalid_ocr():
    stored = _stored_file("empty.png")
    ocr_result = ImageTextResult(
        text="",
        chunk_type="ocr_text",
        processor="ocr",
        confidence=0.0,
        metadata={},
    )
    vision_result = ImageTextResult(
        text="A screenshot of a dashboard with error metrics.",
        chunk_type="image_description",
        processor="vision",
        confidence=0.85,
        metadata={"vision_model": "Qwen3-VL-8B-Instruct"},
    )

    with patch("app.rag.extractors.image_extractor.run_tesseract_ocr", return_value=ocr_result):
        with patch("app.rag.extractors.image_extractor.run_vision", return_value=vision_result):
            docs = smart_image_processing(stored)

    assert len(docs) == 1
    assert docs[0].metadata["chunk_type"] == "image_description"
