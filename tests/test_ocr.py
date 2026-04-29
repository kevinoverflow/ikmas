"""Unit tests for OCR functionality."""

import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

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
from app.rag.ocr import process_image_for_ocr, run_tesseract_ocr
from app.rag.storage import StoredFile


def test_run_tesseract_ocr_basic():
    """Test basic OCR functionality with mock data."""
    mock_img = MagicMock()
    mock_text = "This is a test OCR result"

    with patch("app.rag.ocr.Image") as mock_image_module:
        with patch("app.rag.ocr.pytesseract") as mock_pytesseract:
            mock_image_module.open.return_value = mock_img
            mock_pytesseract.image_to_string.return_value = mock_text
            mock_pytesseract.image_to_data.return_value = {
                "text": ["This", "is", "a", "test", "OCR", "result"],
                "left": [0, 0, 0, 0, 0, 0],
                "top": [0, 0, 0, 0, 0, 0],
                "width": [10, 10, 10, 10, 10, 10],
                "height": [5, 5, 5, 5, 5, 5],
                "conf": ["90", "95", "85", "92", "88", "94"],
            }

            result = run_tesseract_ocr(Path("/fake/path/image.png"))

    assert isinstance(result, ImageTextResult)
    assert result.text == mock_text
    assert result.chunk_type == "ocr_text"
    assert result.processor == "ocr"
    assert result.confidence and result.confidence > 0.0
    assert result.metadata["ocr_engine"] == "tesseract"
    assert result.metadata["ocr_language"] == "eng"
    assert isinstance(result.metadata["bounding_boxes"], list)


def test_run_tesseract_ocr_empty_image():
    """Test OCR with no text detected."""
    mock_img = MagicMock()

    with patch("app.rag.ocr.Image") as mock_image_module:
        with patch("app.rag.ocr.pytesseract") as mock_pytesseract:
            mock_image_module.open.return_value = mock_img
            mock_pytesseract.image_to_string.return_value = ""
            mock_pytesseract.image_to_data.return_value = {
                "text": [],
                "left": [],
                "top": [],
                "width": [],
                "height": [],
                "conf": [],
            }

            result = run_tesseract_ocr(Path("/fake/path/image.png"))

    assert result.text == ""
    assert result.confidence == 0.0
    assert result.metadata["bounding_boxes"] == []


def test_process_image_for_ocr():
    """Test processing an image file for OCR."""
    stored = StoredFile(
        file_id="test-file-id",
        path=Path("/fake/path/test-image.png"),
        original_name="test-image.png",
        size_bytes=1024,
        sha256="test-sha256-hash",
    )

    mock_ocr_result = ImageTextResult(
        text="Test OCR content",
        chunk_type="ocr_text",
        processor="ocr",
        confidence=0.95,
        metadata={
            "ocr_engine": "tesseract",
            "ocr_confidence": 0.95,
            "ocr_language": "eng",
            "bounding_boxes": [(0, 0, 100, 100)],
        },
    )

    with patch("app.rag.ocr.run_tesseract_ocr", return_value=mock_ocr_result):
        result_docs = process_image_for_ocr(stored)

    assert len(result_docs) == 1
    doc = result_docs[0]
    assert doc.page_content == "Test OCR content"
    assert doc.metadata["file_id"] == "test-file-id"
    assert doc.metadata["source"] == "test-image.png"
    assert doc.metadata["chunk_type"] == "ocr_text"
    assert doc.metadata["ocr_engine"] == "tesseract"
    assert doc.metadata["ocr_confidence"] == 0.95
    assert doc.metadata["ocr_language"] == "eng"
    assert doc.metadata["processed_by"] == "ocr"
    assert doc.metadata["confidence"] == 0.95


def test_process_image_for_ocr_no_text():
    """Test processing an image with no OCR text."""
    stored = StoredFile(
        file_id="test-file-id",
        path=Path("/fake/path/test-image.png"),
        original_name="test-image.png",
        size_bytes=1024,
        sha256="test-sha256-hash",
    )

    mock_ocr_result = ImageTextResult(
        text="",
        chunk_type="ocr_text",
        processor="ocr",
        confidence=0.0,
        metadata={
            "ocr_engine": "tesseract",
            "ocr_confidence": 0.0,
            "ocr_language": "eng",
            "bounding_boxes": [],
        },
    )

    with patch("app.rag.ocr.run_tesseract_ocr", return_value=mock_ocr_result):
        result_docs = process_image_for_ocr(stored)

    assert result_docs == []
