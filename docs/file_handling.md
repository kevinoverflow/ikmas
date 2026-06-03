# File Handling

## Overview

IKMAS stores uploaded source files per workspace/collection and exposes them through the Streamlit file workspace UI.

The main pieces are:

- `app/ui/files.py` renders the file list, upload form, and indexing controls.
- `app/rag/storage.py` owns filesystem-safe file operations.
- `data/uploads/<collection_id>/` stores uploaded files for each collection.
- `app/rag/ingest.py` reads stored files and sends chunks to ChromaDB.

File handling is intentionally split so the UI never performs raw path manipulation directly. It delegates persistence operations to `storage.py`.

---

## Storage Layer

The storage API lives in `app/rag/storage.py`.

### Collection Directory

```python
collection_dir(collection_id: str) -> Path
```

Returns the upload directory for a collection:

```text
data/uploads/<safe_collection_id>/
```

The collection id is sanitized with `sanitize_workspace_part(...)` to avoid unsafe path names.

### Saving Uploads

```python
save_upload(
    collection_id: str,
    filename: str,
    data: bytes,
    on_name_conflict: "skip" | "replace" | "rename" = "skip",
) -> tuple[FileStatus, StoredFile | None]
```

Upload behavior:

| Case | Behavior |
|---|---|
| Same file content already exists | `skipped_identical` |
| Same filename, different content, mode `skip` | `skipped_conflict` |
| Same filename, different content, mode `replace` | Atomically replaces the file |
| Same filename, different content, mode `rename` | Saves as `name (1).ext`, `name (2).ext`, etc. |
| No conflict | Saves the file |

Filenames are sanitized with `sanitize_filename(...)`, and writes use `atomic_write(...)` to reduce the chance of partial files.

### Listing Files

```python
list_collection_files(collection_id, exts=(".pdf",)) -> list[StoredFile]
```

Returns metadata for matching files:

```python
StoredFile(
    file_id=str,
    path=Path,
    original_name=str,
    size_bytes=int,
    sha256=str,
)
```

### Deleting Files

```python
delete_file(collection_id: str, filename: str) -> bool
```

Deletes a sanitized filename from the collection directory.

Returns:

- `True` if the file existed and was deleted.
- `False` if no matching file was found.

The Streamlit file workspace should call this helper rather than deleting paths directly.

---

## Streamlit File Workspace

The UI entry point is:

```python
render_file_workspace(collection_id)
```

It renders three areas:

1. File list
2. Upload form
3. Index controls

### File List

`render_file_browser(...)` renders a native Streamlit file list from `list_collection_files(...)`.

The list intentionally shows only:

| Column | Meaning |
|---|---|
| File | Sanitized stored filename with file-type badge |
| Size | Human-readable file size shown as row metadata |
| Download | Per-file `st.download_button(...)` |
| Remove | Per-file delete button |

The UI does not show `Last Modified`. Each file renders as a compact row card with download and remove as row-level accessory actions, so the user does not need to select a file before acting on it.

The filter input performs a case-insensitive filename match:

```python
_filter_stored_files(stored_files, filter_query)
```

Download reads the stored file bytes directly:

```python
stored_file.path.read_bytes()
```

Remove calls:

```python
delete_file(collection_id, filename)
```

On success, the UI shows:

```text
File removed: <filename>
```

Then it calls `st.rerun()` so the browser refreshes.

## Upload Form

The separate upload form uses Streamlit's `st.file_uploader(...)`.

This path goes through the app's storage API and supports deduplication/conflict handling:

```python
save_upload(
    collection_id=collection_id,
    filename=uploaded_file.name,
    data=uploaded_file.getvalue(),
    on_name_conflict=conflict_mode,
)
```

Supported conflict modes:

- `skip`
- `replace`
- `rename`

After saving, the UI shows a summary:

```text
saved=<n>, replaced=<n>, renamed=<n>, skipped_identical=<n>
```

---

## Index Controls

Indexing reads files already stored on disk:

```python
stored_files = list_collection_files(collection_id, exts=SUPPORTED_FILE_EXTENSIONS)
```

When the user clicks `Index now`, the UI:

1. Optionally clears the Chroma collection.
2. Splits each stored file with `split_file(...)`.
3. Chunks documents with `split_documents(...)`.
4. Writes chunks to ChromaDB with `add_docs(...)`.

This means file upload/delete and vector indexing are separate steps. Deleting a source file removes it from disk, but it does not automatically remove already-indexed chunks from ChromaDB unless the user reindexes with clearing enabled.

---

## Testing

Relevant tests:

- `tests/test_storage.py`
- `tests/test_ui_files.py`

Useful focused command:

```bash
./run_tests.sh tests/test_ui_files.py tests/test_storage.py
```

The UI tests cover:

- Native file list rendering.
- Download and remove row actions.
- File summary formatting.
- File size formatting.
