from langchain_core.documents import Document

from app.rag import vectorstore


def test_sanitize_metadata_drops_empty_lists_and_serializes_nested_values():
    metadata = {
        "source": "diagram.png",
        "visual_elements": [],
        "tags": ["diagram", "flow"],
        "bounding_boxes": [(0, 0, 100, 100)],
        "details": {"page": 1},
        "confidence": 0.95,
        "is_visual": True,
        "empty": None,
    }

    sanitized = vectorstore.sanitize_metadata(metadata)

    assert sanitized == {
        "source": "diagram.png",
        "tags": ["diagram", "flow"],
        "bounding_boxes": "[[0, 0, 100, 100]]",
        "details": "{\"page\": 1}",
        "confidence": 0.95,
        "is_visual": True,
    }


def test_add_docs_sanitizes_metadata_before_upsert(monkeypatch):
    seen = {}

    class FakeChroma:
        def add_documents(self, docs):
            seen["docs"] = docs

        def persist(self):
            seen["persisted"] = True

    monkeypatch.setattr(vectorstore, "get_chroma", lambda collection_name: FakeChroma())

    doc = Document(
        page_content="image description",
        metadata={"visual_elements": [], "bounding_boxes": [(1, 2, 3, 4)]},
    )

    count = vectorstore.add_docs("default", [doc])

    assert count == 1
    assert seen["persisted"] is True
    assert seen["docs"][0].metadata == {"bounding_boxes": "[[1, 2, 3, 4]]"}
