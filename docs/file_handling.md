# File Handling

The file workspace is implemented with native Streamlit controls in `app/ui/files.py`. It does not use a third-party file browser component.

## UI Responsibilities

`render_file_workspace(collection_id)` renders:

- current file list
- upload form
- conflict mode selector
- download and remove buttons
- Chroma indexing controls

The UI delegates filesystem operations to `app/rag/storage.py`.

## Storage

Files are stored under:

```text
data/uploads/<safe_collection_id>/
```

`collection_dir(...)` sanitizes collection ids through `sanitize_workspace_part(...)`. `sanitize_filename(...)` strips path components and replaces unsafe characters.

## Upload Behavior

`save_upload(...)` supports:

| Case | Status |
|---|---|
| Same content already exists | `skipped_identical` |
| Same filename, different content, conflict mode `skip` | `skipped_conflict` |
| Same filename, different content, conflict mode `replace` | `replaced` |
| Same filename, different content, conflict mode `rename` | `renamed` |
| New file | `saved` |

Writes are atomic through a temporary file and `os.replace(...)`.

## Listing, Download, Delete

- `list_collection_files(...)` returns `StoredFile` records with path, original name, size, and SHA-256.
- Downloads are Streamlit `download_button(...)` controls that read bytes from the stored path.
- `delete_file(...)` deletes a sanitized filename from the collection directory.

## Indexing

Clicking "Index now" in the UI:

1. optionally clears the Chroma collection,
2. loads all supported stored files,
3. extracts and splits them,
4. writes chunks to Chroma through `add_docs(...)`.

Uploading alone does not index a file; the user must run indexing from the UI.
