from __future__ import annotations

from app.backend.sqlite_store import save_artefacts, save_links


def persist_artefacts_with_links(artefacts: list[dict], citations: list[dict], project: str = "default") -> list[int]:
    if not artefacts:
        return []

    artefact_ids = save_artefacts(artefacts=artefacts, project=project, refs=citations)

    for aid in artefact_ids:
        for c in citations:
            save_links(
                from_type="artefact",
                from_id=str(aid),
                to_type="source",
                to_id=str(c.get("source_id", "unknown")),
                relation="supports",
                confidence=float(c.get("score", 0.0)),
            )

    return artefact_ids
