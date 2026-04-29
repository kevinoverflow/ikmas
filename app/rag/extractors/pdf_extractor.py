"""PDF extractor for IKMAS ingestion system."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import List

import fitz
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document

from app.rag.extractors.image_extractor import extract_image_documents
from app.rag.storage import StoredFile, sha256_bytes

logger = logging.getLogger(__name__)


def _image_filename(stored: StoredFile, page_number: int, image_number: int, xref: int, ext: str) -> str:
    suffix = ext if ext.startswith(".") else f".{ext}"
    return f"{Path(stored.original_name).stem}_page-{page_number:03d}_image-{image_number:03d}_xref-{xref}{suffix}"


def _build_embedded_image_file(
    stored: StoredFile,
    image_path: Path,
    image_bytes: bytes,
    image_name: str,
    page_number: int,
    image_number: int,
    xref: int,
) -> StoredFile:
    image_hash = sha256_bytes(image_bytes)
    return StoredFile(
        file_id=f"{stored.file_id}:page-{page_number}:image-{image_number}:xref-{xref}",
        path=image_path,
        original_name=image_name,
        size_bytes=len(image_bytes),
        sha256=image_hash,
    )


def _annotate_embedded_image_doc(
    doc: Document,
    stored: StoredFile,
    image_file: StoredFile,
    page_number: int,
    image_number: int,
    xref: int,
) -> Document:
    doc.metadata.update(
        {
            "file_id": stored.file_id,
            "source": stored.original_name,
            "embedded_in": "pdf",
            "parent_file_id": stored.file_id,
            "parent_source": stored.original_name,
            "embedded_image_file_id": image_file.file_id,
            "embedded_image_name": image_file.original_name,
            "embedded_image_sha256": image_file.sha256,
            "pdf_page": page_number,
            "pdf_image_index": image_number,
            "pdf_image_xref": xref,
        }
    )
    return doc


def extract_pdf_image_documents(stored: StoredFile) -> List[Document]:
    """Extract embedded PDF images and process them through the image extractor."""
    docs: List[Document] = []

    try:
        pdf = fitz.open(stored.path)
    except Exception as e:
        logger.warning(f"Unable to open PDF images from {stored.original_name}: {e}")
        return docs

    try:
        with tempfile.TemporaryDirectory(prefix="ikmas_pdf_images_") as tmp_dir:
            tmp_path = Path(tmp_dir)

            for page_index in range(len(pdf)):
                page_number = page_index + 1
                page = pdf[page_index]

                for image_index, image_info in enumerate(page.get_images(full=True), start=1):
                    xref = image_info[0]

                    try:
                        extracted = pdf.extract_image(xref)
                        image_bytes = extracted.get("image", b"")
                        if not image_bytes:
                            continue

                        ext = extracted.get("ext") or "png"
                        image_name = _image_filename(stored, page_number, image_index, xref, ext)
                        image_path = tmp_path / image_name
                        image_path.write_bytes(image_bytes)

                        image_file = _build_embedded_image_file(
                            stored=stored,
                            image_path=image_path,
                            image_bytes=image_bytes,
                            image_name=image_name,
                            page_number=page_number,
                            image_number=image_index,
                            xref=xref,
                        )

                        image_docs = extract_image_documents(image_file)
                        docs.extend(
                            _annotate_embedded_image_doc(
                                doc=image_doc,
                                stored=stored,
                                image_file=image_file,
                                page_number=page_number,
                                image_number=image_index,
                                xref=xref,
                            )
                            for image_doc in image_docs
                        )
                    except Exception as e:
                        logger.warning(
                            "Unable to extract embedded image %s on page %s from %s: %s",
                            image_index,
                            page_number,
                            stored.original_name,
                            e,
                        )
    finally:
        pdf.close()

    return docs


def extract_pdf_documents(stored: StoredFile) -> List[Document]:
    try:
        # Load the PDF using PyPDFLoader for text extraction
        loader = PyPDFLoader(str(stored.path))
        docs = loader.load()
        
        # Add metadata to each document
        for doc in docs:
            doc.metadata.update({
                "file_id": stored.file_id,
                "source": stored.original_name,
                "chunk_type": "native_text"
            })
        
        docs.extend(extract_pdf_image_documents(stored))
        
        return docs
        
    except Exception as e:
        logger.error(f"Error extracting PDF documents from {stored.original_name}: {e}")
        # Return a placeholder document if extraction fails
        doc = Document(
            page_content=f"Failed to extract content from PDF: {str(e)}",
            metadata={
                "file_id": stored.file_id,
                "source": stored.original_name,
                "chunk_type": "native_text",
                "error": str(e)
            }
        )
        return [doc]
