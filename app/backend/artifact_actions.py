from __future__ import annotations

from typing import Any

from app.backend.artifact_models import ArtifactGenerationRequest, ArtifactType
from app.backend.orchestrator import _artefacts_from_subagent_result
from app.backend.retrieval import run_retrieval
from app.backend.sqlite_store import (
    delete_artefact,
    get_artefact,
    list_artefacts,
    update_artefact,
)
from app.backend.subagent_coordinator import subagent_coordinator
from app.rag.llm import OpenAIChatBackend


REGENERATION_RETRIEVAL_LIMIT = 8
REGENERATION_RELATED_LIMIT = 8

SUPPORTED_SUBAGENT_ARTIFACT_TYPES = {"definition", "concept", "quiz_item"}


def save_artifact_edits(
    *,
    artefact_id: int,
    title: str,
    content: str,
) -> bool:
    return update_artefact(
        artefact_id,
        title=title.strip() or "Untitled artifact",
        content=content.strip(),
    )


def delete_artifact(*, artefact_id: int) -> bool:
    return delete_artefact(artefact_id)


def regenerate_artifact(
    *,
    artefact_id: int,
    backend: Any | None = None,
) -> dict[str, Any]:
    artifact = get_artefact(artefact_id)
    if artifact is None:
        raise ValueError(f"Artifact {artefact_id} not found")

    backend = backend or OpenAIChatBackend()
    regenerated = _regenerate_with_specific_generator(artifact, backend)
    if regenerated is None:
        regenerated = _regenerate_with_generic_llm(artifact, backend)

    update_artefact(
        artefact_id,
        title=regenerated["title"],
        content=regenerated["content"],
    )
    return {
        **artifact,
        "title": regenerated["title"],
        "content": regenerated["content"],
    }


def _regenerate_with_specific_generator(
    artifact: dict[str, Any],
    backend: Any,
) -> dict[str, Any] | None:
    artifact_type = artifact["type"]
    if artifact_type not in SUPPORTED_SUBAGENT_ARTIFACT_TYPES:
        return None

    related_artifacts = _related_artifacts_for_regeneration(artifact)
    request = ArtifactGenerationRequest(
        artifact_type=ArtifactType(artifact_type),
        context=_build_regeneration_context(
            artifact,
            related_artifacts=related_artifacts,
        ),
        user_input=(
            f"Regenerate a detailed {artifact_type} artifact for '{artifact['title']}'. "
            "Use the source context below when available, preserve the artifact's purpose, "
            "and make the replacement at least as specific and useful as the previous version."
        ),
        session_id=f"regenerate-{artifact['id']}",
        related_artifacts=related_artifacts,
        target_audience="general",
    )
    results = subagent_coordinator.generate_artifacts_sequentially([request], backend)
    for result in results:
        for regenerated in _artefacts_from_subagent_result(result):
            if regenerated["type"] == artifact_type:
                return {
                    "title": regenerated["title"],
                    "content": regenerated["content"],
                }
    return None


def _build_regeneration_context(
    artifact: dict[str, Any],
    *,
    related_artifacts: list[dict[str, Any]] | None = None,
) -> str:
    blocks: list[str] = []
    source_context = _retrieved_source_context_for_regeneration(artifact)
    if source_context:
        blocks.append("Source context from the knowledge base:\n" + source_context)

    blocks.append(
        "Current artifact to improve:\n"
        f"Title: {artifact['title']}\n"
        f"Type: {artifact['type']}\n"
        f"Content:\n{artifact['content']}"
    )

    related_context = _related_artifact_context_for_regeneration(
        artifact,
        related_artifacts=related_artifacts,
    )
    if related_context:
        blocks.append("Related saved artifacts from the same collection:\n" + related_context)

    return "\n\n".join(blocks)


def _retrieved_source_context_for_regeneration(artifact: dict[str, Any]) -> str:
    project = artifact.get("project")
    if not project:
        return ""

    query = f"{artifact.get('title', '')}\n\n{artifact.get('content', '')}"
    try:
        retrieval = run_retrieval(
            query=query,
            collection_name=str(project),
            k_retrieve=30,
            k_final=REGENERATION_RETRIEVAL_LIMIT,
        )
    except Exception:
        return ""

    chunks = retrieval.get("chunks", [])
    if not isinstance(chunks, list):
        return ""

    chunk_texts = [
        str(chunk.get("text") or "").strip()
        for chunk in chunks
        if isinstance(chunk, dict) and str(chunk.get("text") or "").strip()
    ]
    return "\n\n".join(chunk_texts[:REGENERATION_RETRIEVAL_LIMIT])


def _related_artifacts_for_regeneration(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    project = artifact.get("project")
    if not project:
        return []

    try:
        artifacts = list_artefacts(str(project), limit=REGENERATION_RELATED_LIMIT + 1)
    except Exception:
        return []

    return [
        related
        for related in artifacts
        if related.get("id") != artifact.get("id")
    ][:REGENERATION_RELATED_LIMIT]


def _related_artifact_context_for_regeneration(
    artifact: dict[str, Any],
    *,
    related_artifacts: list[dict[str, Any]] | None = None,
) -> str:
    related_artifacts = related_artifacts or _related_artifacts_for_regeneration(artifact)
    lines = []
    for related in related_artifacts:
        content = " ".join(str(related.get("content") or "").split())
        if len(content) > 500:
            content = content[:497].rstrip() + "..."
        lines.append(
            f"- {related.get('type', 'artifact')} | {related.get('title', 'Untitled')}: {content}"
        )
    return "\n".join(lines)


def _regenerate_with_generic_llm(
    artifact: dict[str, Any],
    backend: Any,
) -> dict[str, str]:
    context_content = _build_regeneration_context(artifact)
    prompt = f"""
    Regenerate and improve this artifact while preserving its purpose.
    Make it detailed, specific, and at least as comprehensive as the previous version.

    Type: {artifact['type']}
    Title: {artifact['title']}
    Regeneration context:
    {context_content}

    Return the improved artifact content only. Do not use markdown fences.
    """
    content = backend.generate(prompt, temperature=0.3, max_tokens=1400).strip()
    return {
        "title": artifact["title"],
        "content": content,
    }
