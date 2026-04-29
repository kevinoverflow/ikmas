"""Image extractor for IKMAS ingestion system."""

from __future__ import annotations

from typing import List

from langchain_core.documents import Document
from app.domain.types import ImageTextResult
from app.rag.ocr import OCR_LANGUAGE, is_text_valid, run_tesseract_ocr
from app.rag.storage import StoredFile
from app.rag.vision import run_vision

LOW_OCR_CONFIDENCE = 0.6
VISION_FILENAME_HINTS = (
    "chart",
    "diagram",
    "figure",
    "flow",
    "graph",
    "plot",
    "screenshot",
    "screen-shot",
    "dashboard",
    "ui",
    "wireframe",
)


def _build_document(stored: StoredFile, result: ImageTextResult) -> Document:
    metadata = {
        "file_id": stored.file_id,
        "source": stored.original_name,
        "chunk_type": result.chunk_type,
        "media_type": "image",
        "processed_by": result.processor,
    }
    metadata.update(result.metadata)
    if result.confidence is not None:
        metadata["confidence"] = result.confidence

    return Document(page_content=result.text, metadata=metadata)


def _filename_suggests_visual_content(filename: str) -> bool:
    normalized = filename.lower()
    return any(keyword in normalized for keyword in VISION_FILENAME_HINTS)


def should_run_vision(stored: StoredFile, ocr_result: ImageTextResult) -> bool:
    if not is_text_valid(ocr_result.text):
        return True

    confidence = ocr_result.confidence or 0.0
    if confidence < LOW_OCR_CONFIDENCE:
        return True

    return _filename_suggests_visual_content(stored.original_name)


def extract_image_documents(stored: StoredFile, lang: str = OCR_LANGUAGE) -> List[Document]:
    """
    Extract documents from an image file.

    OCR and vision stay separate concerns at the utility layer; this extractor
    converts their outputs into retrieval-ready LangChain Documents.
    """
    docs: List[Document] = []

    ocr_result = run_tesseract_ocr(stored.path, lang)
    if is_text_valid(ocr_result.text):
        docs.append(_build_document(stored, ocr_result))

    if should_run_vision(stored, ocr_result):
        vision_result = run_vision(stored.path)
        if vision_result is not None and vision_result.text.strip():
            docs.append(_build_document(stored, vision_result))

    return docs


def smart_image_processing(stored: StoredFile, lang: str = OCR_LANGUAGE) -> List[Document]:
    """Compatibility wrapper for the old image-processing entry point."""
    return extract_image_documents(stored, lang=lang)
