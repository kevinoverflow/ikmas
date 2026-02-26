from pathlib import Path

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
