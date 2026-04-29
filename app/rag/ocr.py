from typing import List
from pathlib import Path
from langchain_core.documents import Document
from app.domain.types import ImageTextResult
from app.rag.storage import StoredFile
import pytesseract
from PIL import Image
import logging
import re

logger = logging.getLogger(__name__)

OCR_LANGUAGE = "eng"  # English as default

def _build_ocr_document(stored: StoredFile, result: ImageTextResult) -> Document:
    metadata = {
        "file_id": stored.file_id,
        "source": stored.original_name,
        "chunk_type": result.chunk_type,
        "processed_by": result.processor,
    }
    metadata.update(result.metadata)
    if result.confidence is not None:
        metadata["confidence"] = result.confidence

    return Document(page_content=result.text, metadata=metadata)


def run_tesseract_ocr(image_path: Path, lang: str = OCR_LANGUAGE) -> ImageTextResult:
    try:
        img = Image.open(image_path)

        ocr_data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT, lang=lang)
        text = pytesseract.image_to_string(img, lang=lang)

        confidences = []
        for conf in ocr_data.get("conf", []):
            try:
                confidence = float(conf)
            except (TypeError, ValueError):
                continue
            if confidence >= 0:
                confidences.append(confidence)

        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        normalized_confidence = avg_confidence / 100.0
        bounding_boxes = [
            (x, y, w, h)
            for x, y, w, h in zip(
                ocr_data.get("left", []),
                ocr_data.get("top", []),
                ocr_data.get("width", []),
                ocr_data.get("height", []),
            )
        ]

        return ImageTextResult(
            text=text.strip(),
            chunk_type="ocr_text",
            processor="ocr",
            confidence=normalized_confidence,
            metadata={
                "ocr_engine": "tesseract",
                "ocr_language": lang,
                "ocr_confidence": normalized_confidence,
                "bounding_boxes": bounding_boxes,
            },
        )
    except Exception as e:
        logger.error(f"Error running OCR on {image_path}: {e}")
        return ImageTextResult(
            text="",
            chunk_type="ocr_text",
            processor="ocr",
            confidence=0.0,
            metadata={
                "ocr_engine": "tesseract",
                "ocr_language": lang,
                "ocr_confidence": 0.0,
                "bounding_boxes": [],
            },
        )


def is_text_valid(text: str, min_length: int = 10, min_words: int = 3) -> bool:
    if not text:
        return False
    
    # Remove extra whitespace
    clean_text = text.strip()
    
    # Check minimum length
    if len(clean_text) < min_length:
        return False
    
    # Check minimum word count
    words = clean_text.split()
    if len(words) < min_words:
        return False
    
    # Check for reasonable text patterns (avoid gibberish)
    # Remove common non-text patterns
    if re.search(r'^[0-9\s]+$', clean_text):  # Only digits and spaces
        return False
        
    # Simple heuristic: at least 30% alphanumeric characters
    alpha_chars = sum(1 for c in clean_text if c.isalnum())
    if len(clean_text) > 0 and alpha_chars / len(clean_text) < 0.3:
        return False
    
    return True


def process_image_for_ocr(stored: StoredFile, lang: str = OCR_LANGUAGE) -> List[Document]:
    ocr_result = run_tesseract_ocr(stored.path, lang)

    if not is_text_valid(ocr_result.text):
        return []

    return [_build_ocr_document(stored, ocr_result)]
