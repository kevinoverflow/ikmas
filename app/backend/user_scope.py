from __future__ import annotations

import hashlib
import re


WORKSPACE_ID_SAFE_RE = re.compile(r"[^A-Za-z0-9_-]+")
MAX_CHROMA_COLLECTION_LENGTH = 63


def sanitize_workspace_part(value: str | None, fallback: str = "workspace") -> str:
    """
    Normalize a user-controlled identifier for use in local paths and Chroma names.
    """
    cleaned = WORKSPACE_ID_SAFE_RE.sub("_", (value or "").strip())
    cleaned = cleaned.strip("_-")

    if not cleaned:
        cleaned = fallback

    if not cleaned[0].isalnum():
        cleaned = f"{fallback}_{cleaned}"

    if not cleaned[-1].isalnum():
        cleaned = f"{cleaned}_{fallback}"

    return cleaned


def user_workspace_id(user_id: str, logical_collection: str = "default") -> str:
    """
    Return the private collection/upload namespace for one authenticated user.

    Chroma collection names have a short length limit, so long logical collection
    names are compacted with a stable hash suffix instead of being rejected.
    """
    user_part = sanitize_workspace_part(user_id, fallback="user")
    collection_part = sanitize_workspace_part(logical_collection, fallback="default")
    workspace_id = f"u_{user_part}__{collection_part}"

    if len(workspace_id) <= MAX_CHROMA_COLLECTION_LENGTH:
        return workspace_id

    digest = hashlib.sha256(workspace_id.encode("utf-8")).hexdigest()[:12]
    fixed_chars = len("u_") + len("__") + len("_") + len(digest)
    available = MAX_CHROMA_COLLECTION_LENGTH - fixed_chars
    user_budget = max(8, min(len(user_part), available // 2))
    collection_budget = max(3, available - user_budget)
    compact = f"u_{user_part[:user_budget]}__{collection_part[:collection_budget]}_{digest}"

    return compact[:MAX_CHROMA_COLLECTION_LENGTH].strip("_-")
