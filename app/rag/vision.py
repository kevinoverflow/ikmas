import base64
import mimetypes
from typing import List
from pathlib import Path
from langchain_core.documents import Document
from app.domain.types import ImageTextResult
from app.rag.storage import StoredFile
from app.infrastructure.config import API_KEY, BASE_URL
from app.infrastructure.tracing import maybe_wrap_openai
from openai import OpenAI
import logging

logger = logging.getLogger(__name__)
VISION_MODEL = "Qwen/Qwen3-VL-8B-Instruct"
VISION_PROMPT = (
    "Describe this image for search and retrieval. Include visible text, the main visual "
    "elements, and the meaning of any chart, diagram, screenshot, or figure."
)


def _detect_image_media_type(image_path: Path) -> str:
    media_type, _ = mimetypes.guess_type(str(image_path))
    return media_type or "image/jpeg"


def _coerce_response_text(content) -> str:
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text")
                if text:
                    parts.append(text)
        return "\n".join(part for part in parts if part).strip()

    return str(content).strip()


def _build_vision_document(stored: StoredFile, result: ImageTextResult) -> Document:
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


def run_vision(image_path: Path) -> ImageTextResult | None:
    try:
        with open(image_path, "rb") as image_file:
            encoded_image = base64.b64encode(image_file.read()).decode("utf-8")

        if not API_KEY:
            raise RuntimeError("Missing API key (SCADS_API_KEY / OPENAI_API_KEY).")

        media_type = _detect_image_media_type(image_path)
        client = maybe_wrap_openai(OpenAI(base_url=BASE_URL, api_key=API_KEY))
        response = client.chat.completions.create(
            model=VISION_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": VISION_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{media_type};base64,{encoded_image}"},
                        },
                    ],
                }
            ],
            temperature=0.2,
        )
        response_text = _coerce_response_text(response.choices[0].message.content)
        if not response_text:
            return None

        return ImageTextResult(
            text=response_text,
            chunk_type="image_description",
            processor="vision",
            confidence=0.95,
            metadata={
                "vision_model": VISION_MODEL,
                "visual_elements": [],
            },
        )
    except Exception as e:
        logger.error(f"Error running vision processing on {image_path}: {e}")
        return None


def process_image_with_vision(stored: StoredFile) -> List[Document]:
    vision_result = run_vision(stored.path)

    if vision_result is None or not vision_result.text.strip():
        return []

    return [_build_vision_document(stored, vision_result)]
