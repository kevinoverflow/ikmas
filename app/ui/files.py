from __future__ import annotations

from html import escape
from collections import Counter
from pathlib import Path

import streamlit as st

from app.rag.storage import StoredFile, delete_file, list_collection_files, save_upload
from app.ui.constants import SUPPORTED_FILE_EXTENSIONS, SUPPORTED_UPLOAD_TYPES


def render_file_workspace(collection_id: str) -> None:
    render_file_browser(collection_id)

    st.divider()
    render_upload_form(collection_id)

    st.divider()
    render_index_controls(collection_id)


def render_file_browser(collection_id: str) -> None:
    st.subheader("Deine Dateien")
    _inject_file_workspace_styles()

    stored_files = list_collection_files(collection_id, exts=SUPPORTED_FILE_EXTENSIONS)
    if not stored_files:
        st.info("No files uploaded yet.")
        return

    filter_query = st.text_input(
        "Filter files",
        key=f"file_filter_{collection_id}",
        placeholder="Filter files",
        label_visibility="collapsed",
    )
    filtered_files = _filter_stored_files(stored_files, filter_query)

    if not filtered_files:
        st.info("No files match the current filter.")
        return

    st.caption(f"{len(filtered_files)} file{'s' if len(filtered_files) != 1 else ''}")
    for stored_file in filtered_files:
        _render_file_row(collection_id, stored_file)


def render_upload_form(collection_id: str) -> None:
    st.subheader("Neue Dateien hinzufügen")
    uploaded_files = st.file_uploader(
        "Dateien auswählen (PDF, DOCX, PPTX, TXT, MD)",
        type=SUPPORTED_UPLOAD_TYPES,
        accept_multiple_files=True,
    )

    conflict_mode = st.selectbox(
        "Bei Namenskonflikt:",
        ["skip", "replace", "rename"],
        index=0,
    )

    if not uploaded_files or not st.button("Speichern (mit Dedupe)", type="primary"):
        return

    upload_counts = Counter()
    for uploaded_file in uploaded_files:
        status, _ = save_upload(
            collection_id=collection_id,
            filename=uploaded_file.name,
            data=uploaded_file.getvalue(),
            on_name_conflict=conflict_mode,
        )
        upload_counts[status] += 1

    st.success(_format_upload_summary(upload_counts))
    st.rerun()


def render_index_controls(collection_id: str) -> None:
    st.subheader("Index (Chroma) aus serverseitigen Dateien")
    reindex = st.checkbox("Reindex (Chroma collection vorher leeren)", value=False)
    stored_files = list_collection_files(collection_id, exts=SUPPORTED_FILE_EXTENSIONS)

    if not st.button("Index now", type="primary", disabled=len(stored_files) == 0):
        return

    from app.rag.ingest import split_documents, split_file
    from app.rag.vectorstore import add_docs, clear_collection

    with st.spinner("Chunking + Embedding + Writing to Chroma..."):
        if reindex:
            clear_collection(collection_id)

        docs = []
        for stored_file in stored_files:
            docs.extend(split_documents(split_file(stored_file)))

        chunk_count = add_docs(collection_id, docs)
        st.session_state.docs_indexed = True

    st.success(f"Indexed {chunk_count} chunks")


def _format_upload_summary(upload_counts: Counter) -> str:
    return (
        f"saved={upload_counts['saved']}, "
        f"replaced={upload_counts['replaced']}, "
        f"renamed={upload_counts['renamed']}, "
        f"skipped_identical={upload_counts['skipped_identical']}"
    )


def _inject_file_workspace_styles() -> None:
    st.markdown(
        """
        <style>
        .ikmas-file-main {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            min-width: 0;
        }

        .ikmas-file-icon {
            align-items: center;
            background: #eef6ff;
            border: 1px solid #c9e2ff;
            border-radius: 8px;
            color: #1f6feb;
            display: inline-flex;
            flex: 0 0 auto;
            font-size: 1rem;
            height: 2.25rem;
            justify-content: center;
            width: 2.25rem;
        }

        .ikmas-file-copy {
            min-width: 0;
        }

        .ikmas-file-name {
            color: #1f2937;
            font-weight: 650;
            line-height: 1.2;
            overflow-wrap: anywhere;
        }

        .ikmas-file-meta {
            align-items: center;
            color: #6b7280;
            display: flex;
            flex-wrap: wrap;
            font-size: 0.8rem;
            gap: 0.4rem;
            line-height: 1.3;
            margin-top: 0.2rem;
        }

        .ikmas-file-badge {
            background: #f3f4f6;
            border: 1px solid #e5e7eb;
            border-radius: 999px;
            color: #374151;
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0;
            padding: 0.05rem 0.42rem;
            text-transform: uppercase;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _filter_stored_files(files: list[StoredFile], query: str) -> list[StoredFile]:
    query = query.strip().lower()
    if not query:
        return files

    return [stored_file for stored_file in files if query in stored_file.original_name.lower()]


def _render_file_row(collection_id: str, stored_file: StoredFile) -> None:
    with st.container(border=True):
        file_col, download_col, delete_col = st.columns(
            [6, 1.15, 1.15],
            vertical_alignment="center",
        )
        file_col.markdown(_format_file_summary(stored_file), unsafe_allow_html=True)

        download_col.download_button(
            "Download",
            data=_read_file_bytes(stored_file.path),
            file_name=stored_file.original_name,
            mime="application/octet-stream",
            key=f"download_{collection_id}_{stored_file.sha256}",
            icon=":material/download:",
            use_container_width=True,
        )

        if delete_col.button(
            "Remove",
            key=f"delete_{collection_id}_{stored_file.sha256}",
            icon=":material/delete:",
            use_container_width=True,
        ):
            if delete_file(collection_id, stored_file.original_name):
                st.success(f"File removed: {stored_file.original_name}")
                st.rerun()


def _format_file_summary(stored_file: StoredFile) -> str:
    filename = escape(stored_file.original_name)
    extension = escape(_file_extension_label(stored_file.original_name))
    size = escape(_format_file_size(stored_file.size_bytes))
    icon = _file_icon(stored_file.original_name)
    return f"""
    <div class="ikmas-file-main">
        <div class="ikmas-file-icon">{icon}</div>
        <div class="ikmas-file-copy">
            <div class="ikmas-file-name">{filename}</div>
            <div class="ikmas-file-meta">
                <span class="ikmas-file-badge">{extension}</span>
                <span>{size}</span>
            </div>
        </div>
    </div>
    """


def _file_extension_label(filename: str) -> str:
    suffix = Path(filename).suffix.lower().lstrip(".")
    return suffix or "file"


def _file_icon(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        return "PDF"
    if suffix in {".md", ".txt"}:
        return "TXT"
    if suffix == ".docx":
        return "DOC"
    if suffix == ".pptx":
        return "PPT"
    return "FILE"


def _read_file_bytes(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError:
        return b""


def _format_file_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"

    size_kb = size_bytes / 1024
    if size_kb < 1024:
        return f"{size_kb:.0f} kB"

    size_mb = size_kb / 1024
    return f"{size_mb:.1f} MB"
