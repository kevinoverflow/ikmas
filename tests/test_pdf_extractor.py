from pathlib import Path

from langchain_core.documents import Document

from app.rag.extractors import pdf_extractor
from app.rag.storage import StoredFile


def _stored_file(name: str = "source.pdf") -> StoredFile:
    return StoredFile(
        file_id="pdf-file-id",
        path=Path("/tmp") / name,
        original_name=name,
        size_bytes=2048,
        sha256="pdf-sha256",
    )


class FakePyPDFLoader:
    def __init__(self, path: str):
        self.path = path

    def load(self):
        return [Document(page_content="native pdf text", metadata={"page": 0})]


class FakePage:
    def __init__(self, image_refs):
        self.image_refs = image_refs

    def get_images(self, full=True):
        assert full is True
        return [(xref,) for xref in self.image_refs]


class FakePDF:
    def __init__(self):
        self.pages = [FakePage([11, 12]), FakePage([])]
        self.closed = False

    def __len__(self):
        return len(self.pages)

    def __getitem__(self, index):
        return self.pages[index]

    def extract_image(self, xref: int):
        return {"image": f"image-{xref}".encode(), "ext": "png"}

    def close(self):
        self.closed = True


def test_extract_pdf_documents_processes_embedded_images(monkeypatch):
    stored = _stored_file()
    fake_pdf = FakePDF()
    seen_image_files = []

    def fake_extract_image_documents(image_file):
        seen_image_files.append(image_file)
        return [
            Document(
                page_content=f"processed {image_file.original_name}",
                metadata={"chunk_type": "ocr_text", "source": image_file.original_name},
            )
        ]

    monkeypatch.setattr(pdf_extractor, "PyPDFLoader", FakePyPDFLoader)
    monkeypatch.setattr(pdf_extractor.fitz, "open", lambda path: fake_pdf)
    monkeypatch.setattr(pdf_extractor, "extract_image_documents", fake_extract_image_documents)

    docs = pdf_extractor.extract_pdf_documents(stored)

    assert fake_pdf.closed is True
    assert len(docs) == 3
    assert docs[0].page_content == "native pdf text"
    assert docs[0].metadata["chunk_type"] == "native_text"

    image_docs = docs[1:]
    assert [image_file.original_name for image_file in seen_image_files] == [
        "source_page-001_image-001_xref-11.png",
        "source_page-001_image-002_xref-12.png",
    ]
    assert [image_file.path.exists() for image_file in seen_image_files] == [False, False]
    assert [doc.metadata["source"] for doc in image_docs] == ["source.pdf", "source.pdf"]
    assert [doc.metadata["embedded_in"] for doc in image_docs] == ["pdf", "pdf"]
    assert [doc.metadata["pdf_page"] for doc in image_docs] == [1, 1]
    assert [doc.metadata["pdf_image_index"] for doc in image_docs] == [1, 2]
    assert [doc.metadata["pdf_image_xref"] for doc in image_docs] == [11, 12]
    assert image_docs[0].metadata["embedded_image_name"] == "source_page-001_image-001_xref-11.png"


def test_extract_pdf_documents_keeps_text_when_image_extraction_fails(monkeypatch):
    stored = _stored_file()

    monkeypatch.setattr(pdf_extractor, "PyPDFLoader", FakePyPDFLoader)
    monkeypatch.setattr(pdf_extractor.fitz, "open", lambda path: (_ for _ in ()).throw(RuntimeError("boom")))

    docs = pdf_extractor.extract_pdf_documents(stored)

    assert len(docs) == 1
    assert docs[0].page_content == "native pdf text"
    assert docs[0].metadata["source"] == "source.pdf"
