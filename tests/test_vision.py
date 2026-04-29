"""Unit tests for vision functionality."""

import sys
import types
from pathlib import Path
from unittest.mock import mock_open, patch

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
from app.rag.storage import StoredFile
from app.rag.vision import process_image_with_vision, run_vision


def test_run_vision_basic():
    """Test basic vision processing functionality."""
    class FakeResponse:
        class Choice:
            class Message:
                content = "A screenshot with a chart and labels."

            message = Message()

        choices = [Choice()]

    class FakeCompletions:
        def create(self, **kwargs):
            return FakeResponse()

    class FakeChat:
        completions = FakeCompletions()

    class FakeClient:
        chat = FakeChat()

    with patch("app.rag.vision.API_KEY", "test-key"):
        with patch("app.rag.vision.OpenAI", return_value=FakeClient()):
            with patch("builtins.open", mock_open(read_data=b"image-bytes")):
                result = run_vision(Path("/fake/path/image.png"))

    assert isinstance(result, ImageTextResult)
    assert result.text == "A screenshot with a chart and labels."
    assert result.chunk_type == "image_description"
    assert result.processor == "vision"
    assert result.metadata["vision_model"] == "Qwen3-VL-8B-Instruct"
    assert isinstance(result.metadata["visual_elements"], list)


def test_process_image_with_vision():
    """Test processing an image with vision."""
    stored = StoredFile(
        file_id="test-file-id",
        path=Path("/fake/path/test-image.png"),
        original_name="test-image.png",
        size_bytes=1024,
        sha256="test-sha256-hash",
    )

    vision_result = ImageTextResult(
        text="Diagram showing three connected services.",
        chunk_type="image_description",
        processor="vision",
        confidence=0.9,
        metadata={
            "vision_model": "Qwen3-VL-8B-Instruct",
            "visual_elements": ["diagram"],
        },
    )

    with patch("app.rag.vision.run_vision", return_value=vision_result):
        result_docs = process_image_with_vision(stored)

    assert len(result_docs) == 1
    doc = result_docs[0]
    assert doc.page_content == "Diagram showing three connected services."
    assert doc.metadata["file_id"] == "test-file-id"
    assert doc.metadata["source"] == "test-image.png"
    assert doc.metadata["chunk_type"] == "image_description"
    assert doc.metadata["vision_model"] == "Qwen3-VL-8B-Instruct"
    assert doc.metadata["processed_by"] == "vision"
    assert doc.metadata["confidence"] == 0.9


def test_error_handling():
    """Test error handling in vision processing."""
    assert run_vision(Path("/nonexistent/path.png")) is None
