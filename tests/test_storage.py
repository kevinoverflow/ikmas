from pathlib import Path

from app.backend import sqlite_store
from app.rag import storage


def test_save_upload_and_identical_skip(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "UPLOAD_DIR", tmp_path)

    status1, info1 = storage.save_upload("default", "doc.pdf", b"abc", on_name_conflict="skip")
    assert status1 == "saved"
    assert info1 is not None
    assert (tmp_path / "default" / "doc.pdf").exists()

    status2, info2 = storage.save_upload("default", "doc2.pdf", b"abc", on_name_conflict="skip")
    assert status2 == "skipped_identical"
    assert info2 is None


def test_save_upload_conflict_modes(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "UPLOAD_DIR", tmp_path)

    storage.save_upload("default", "doc.pdf", b"v1", on_name_conflict="skip")

    status_skip, _ = storage.save_upload("default", "doc.pdf", b"v2", on_name_conflict="skip")
    assert status_skip == "skipped_conflict"
    assert (tmp_path / "default" / "doc.pdf").read_bytes() == b"v1"

    status_replace, _ = storage.save_upload("default", "doc.pdf", b"v2", on_name_conflict="replace")
    assert status_replace == "replaced"
    assert (tmp_path / "default" / "doc.pdf").read_bytes() == b"v2"

    status_rename, info_rename = storage.save_upload("default", "doc.pdf", b"v3", on_name_conflict="rename")
    assert status_rename == "renamed"
    assert info_rename is not None
    assert info_rename.path.name == "doc (1).pdf"
    assert (tmp_path / "default" / "doc (1).pdf").read_bytes() == b"v3"


def test_get_file_path_and_delete(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "UPLOAD_DIR", tmp_path)

    storage.save_upload("default", "doc.pdf", b"data", on_name_conflict="skip")

    p = storage.get_file_path("default", "doc.pdf")
    assert isinstance(p, Path)
    assert p is not None and p.exists()

    assert storage.delete_file("default", "doc.pdf") is True
    assert storage.get_file_path("default", "doc.pdf") is None
    assert storage.delete_file("default", "doc.pdf") is False


def test_collection_id_is_sanitized_to_stay_under_upload_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "UPLOAD_DIR", tmp_path)

    status, info = storage.save_upload("../other-user", "doc.pdf", b"data", on_name_conflict="skip")

    assert status == "saved"
    assert info is not None
    assert info.path == tmp_path / "other-user" / "doc.pdf"
    assert not (tmp_path.parent / "other-user" / "doc.pdf").exists()


def test_list_and_find_artefacts_from_sqlite(tmp_path, monkeypatch):
    monkeypatch.setattr(sqlite_store, "DB_PATH", tmp_path / "ikmas.db")
    sqlite_store.init_db()

    sqlite_store.save_artefacts(
        [
            {
                "type": "definition",
                "title": "RAG",
                "content": "Retrieval augmented generation.",
                "concept_ids": [],
            },
            {
                "type": "concept",
                "title": "SECI",
                "content": "Knowledge conversion model.",
                "concept_ids": [],
            },
        ],
        project="team-space",
        refs=[],
    )

    listed = sqlite_store.list_artefacts("team-space")
    found = sqlite_store.find_similar_artefacts(
        project="team-space",
        artifact_type="definition",
        query="Define RAG",
    )

    assert {artifact["title"] for artifact in listed} == {"RAG", "SECI"}
    assert [artifact["title"] for artifact in found] == ["RAG"]


def test_update_and_delete_artefact(tmp_path, monkeypatch):
    monkeypatch.setattr(sqlite_store, "DB_PATH", tmp_path / "ikmas.db")
    sqlite_store.init_db()
    artefact_id = sqlite_store.save_artefacts(
        [
            {
                "type": "definition",
                "title": "Old",
                "content": "Old content",
                "concept_ids": [],
            }
        ],
        project="team-space",
        refs=[],
    )[0]

    assert sqlite_store.update_artefact(
        artefact_id,
        title="New",
        content="New content",
    )
    updated = sqlite_store.get_artefact(artefact_id)
    assert updated is not None
    assert updated["title"] == "New"
    assert updated["content"] == "New content"

    assert sqlite_store.delete_artefact(artefact_id)
    assert sqlite_store.get_artefact(artefact_id) is None
