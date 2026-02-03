# storage.py
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import hashlib
import os 
import re 
import tempfile
from typing import Dict, List, Literal, Optional, Tuple

from app.infrastructure.config import UPLOAD_DIR

ConflictAction = Literal["skip", "replace", "rename"]
FileStatus = Literal["saved", "skipped_identical", "skipped_conflict", "replaced", "renamed"]

FILENAME_SAFE_RE = re.compile(r"[^A-Za-z0-9.\- _()]+")

@dataclass(frozen=True)
class StoredFile:
    file_id: str
    path: Path
    original_name: str
    size_bytes: int
    sha256: str

def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)

def sanitize_filename(name: str) -> str:
    """
    Prevent path traversal and weird chars.
    """
    name = Path(name).name  # drop any directories
    name = name.strip()
    name = FILENAME_SAFE_RE.sub("_", name)
    if not name:
        name = "upload.pdf"
    return name

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()

def atomic_write(target_path: Path, data: bytes) -> None:
    """
    Atomic write: write temp file in same directory, then os.replace.
    """
    ensure_dir(target_path.parent)
    fd, tmp_path = tempfile.mkstemp(prefix=".upload_", suffix=".tmp", dir=str(target_path.parent))
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, target_path)  # atomic commit / replace
    finally:
        # cleanup if replace failed
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except OSError:
            pass

def list_collection_files(collection_id: str, exts: Tuple[str, ...] = (".pdf",)) -> List[StoredFile]:
    """
    Loads existing files from data/uploads/<collection_id>/ and returns their metadata + hashes.
    """
    coll_dir = UPLOAD_DIR / collection_id
    ensure_dir(coll_dir)

    out: List[StoredFile] = []
    for p in sorted(coll_dir.iterdir()):
        if not p.is_file():
            continue
        if exts and p.suffix.lower() not in exts:
            continue

        try:
            sha = sha256_file(p)
            out.append(
                StoredFile(
                    file_id=p.stem,  # not always hash-based, but fine
                    path=p,
                    original_name=p.name,
                    size_bytes=p.stat().st_size,
                    sha256=sha,
                )
            )
        except OSError:
            continue
    return out

def unique_name(coll_dir: Path, desired_name: str) -> str:
    """
    If desired name exists, append (1), (2), ...
    """
    desired_name = sanitize_filename(desired_name)
    base = Path(desired_name).stem
    ext = Path(desired_name).suffix or ""
    candidate = desired_name
    i = 1
    while (coll_dir / candidate).exists():
        candidate = f"{base} ({i}){ext}"
        i += 1
    return candidate
def save_upload(
    collection_id: str,
    filename: str,
    data: bytes,
    on_name_conflict: ConflictAction = "skip",
) -> Tuple[FileStatus, Optional[StoredFile]]:
    """
    Stores a file in: data/uploads/<collection_id>/<filename>

    Rules:
    - If identical content already exists in this collection (hash match) -> skipped_identical
    - If same filename exists but different content -> apply on_name_conflict:
        skip    -> skipped_conflict
        replace -> replaced (atomic)
        rename  -> renamed (stores with 'name (1).pdf', etc.)
    - Otherwise -> saved

    Returns:
      (status, StoredFile|None)
    """
    safe_name = sanitize_filename(filename)
    new_hash = sha256_bytes(data)

    coll_dir = UPLOAD_DIR / collection_id
    ensure_dir(coll_dir)

    existing = list_collection_files(collection_id)
    by_name: Dict[str, StoredFile] = {f.path.name: f for f in existing}
    existing_hashes = {f.sha256 for f in existing}

    # 1) identical content exists somewhere -> skip
    if new_hash in existing_hashes:
        return "skipped_identical", None

    target = coll_dir / safe_name

    # 2) same filename exists but different content
    if target.exists():
        if on_name_conflict == "skip":
            return "skipped_conflict", None

        if on_name_conflict == "replace":
            atomic_write(target, data)
            info = StoredFile(
                file_id=new_hash[:16],
                path=target,
                original_name=filename,
                size_bytes=len(data),
                sha256=new_hash,
            )
            return "replaced", info

        if on_name_conflict == "rename":
            renamed = unique_name(coll_dir, safe_name)
            new_target = coll_dir / renamed
            atomic_write(new_target, data)
            info = StoredFile(
                file_id=new_hash[:16],
                path=new_target,
                original_name=filename,
                size_bytes=len(data),
                sha256=new_hash,
            )
            return "renamed", info

        raise ValueError(f"Unknown on_name_conflict: {on_name_conflict}")

    # 3) no conflict -> save
    atomic_write(target, data)
    info = StoredFile(
        file_id=new_hash[:16],
        path=target,
        original_name=filename,
        size_bytes=len(data),
        sha256=new_hash,
    )
    return "saved", info

def delete_file(collection_id: str, filename: str) -> bool:
    """
    Deletes a file from data/uploads/<collection_id>/<filename>.
    Returns True if deleted, False if not found.
    """
    safe = sanitize_filename(filename)
    path = UPLOAD_DIR / collection_id / safe
    if not path.exists() or not path.is_file():
        return False
    path.unlink()
    return True

def get_file_path(collection_id: str, filename: str) -> Optional[Path]:
    safe = sanitize_filename(filename)
    path = UPLOAD_DIR / collection_id / safe
    return path if path.exists and path.is_file() else None

def list_filenames(collection_id: str) -> List[str]:
    return [f.path.name for f in list_collection_files(collection_id)]
