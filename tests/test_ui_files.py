from __future__ import annotations

from pathlib import Path

from app.rag import storage
from app.ui.files import (
    _file_extension_label,
    _format_file_size,
    _format_file_summary,
    render_file_browser,
)


class FakeContainer:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class FakeColumn:
    def __init__(self, calls):
        self.calls = calls

    def markdown(self, text, **kwargs):
        self.calls["markdown"].append((text, kwargs))

    def download_button(self, *args, **kwargs):
        self.calls["download_button"].append((args, kwargs))
        return False

    def button(self, *args, **kwargs):
        self.calls["button"].append((args, kwargs))
        return False


def test_render_file_browser_shows_download_and_remove_actions(tmp_path, monkeypatch):
    calls = {"markdown": [], "download_button": [], "button": []}
    monkeypatch.setattr(storage, "UPLOAD_DIR", tmp_path)
    monkeypatch.setattr("app.ui.files.st.markdown", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("app.ui.files.st.subheader", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("app.ui.files.st.caption", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("app.ui.files.st.text_input", lambda *_args, **_kwargs: "")
    monkeypatch.setattr("app.ui.files.st.container", lambda *_args, **_kwargs: FakeContainer())
    monkeypatch.setattr(
        "app.ui.files.st.columns",
        lambda *_args, **_kwargs: [FakeColumn(calls) for _ in range(3)],
    )

    storage.save_upload("ui-test-workspace", "decision-notes.md", b"notes")

    render_file_browser("ui-test-workspace")

    rendered_markdown = "\n".join(text for text, _kwargs in calls["markdown"])
    assert "decision-notes.md" in rendered_markdown
    assert "ikmas-file-badge" in rendered_markdown
    assert "md" in rendered_markdown
    assert calls["download_button"][0][0][0] == "Download"
    assert calls["download_button"][0][1]["file_name"] == "decision-notes.md"
    assert calls["button"][0][0][0] == "Remove"


def test_format_file_size():
    assert _format_file_size(12) == "12 B"
    assert _format_file_size(22 * 1024) == "22 kB"
    assert _format_file_size(2 * 1024 * 1024) == "2.0 MB"


def test_format_file_summary_escapes_filename():
    stored_file = storage.StoredFile(
        file_id="x",
        path=Path("unsafe.md"),
        original_name="<script>.md",
        size_bytes=1024,
        sha256="abc",
    )

    summary = _format_file_summary(stored_file)

    assert "&lt;script&gt;.md" in summary
    assert "<script>" not in summary
    assert _file_extension_label("notes.md") == "md"
