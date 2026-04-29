"""Test for OCR language configuration."""

import sys
import types
from pathlib import Path
from unittest.mock import patch, MagicMock

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

from app.rag.ocr import OCR_LANGUAGE, run_tesseract_ocr, process_image_for_ocr
from app.rag.storage import StoredFile


def test_ocr_language_config():
    """Test OCR language configuration."""
    
    # Test default language
    assert OCR_LANGUAGE == "eng", "Default OCR language should be 'eng'"
    
    print("✓ OCR language configuration test passed")


def test_ocr_with_language_param():
    """Test OCR function with custom language parameter."""
    
    # Test that function accepts language parameter
    import inspect
    sig = inspect.signature(run_tesseract_ocr)
    assert 'lang' in sig.parameters, "run_tesseract_ocr should accept 'lang' parameter"
    
    print("✓ OCR language parameter test passed")


if __name__ == "__main__":
    print("Testing OCR language configuration...")
    try:
        test_ocr_language_config()
        test_ocr_with_language_param()
        print("\n✓ All OCR language tests passed!")
    except Exception as e:
        print(f"\n✗ OCR language test failed: {e}")
        sys.exit(1)