from __future__ import annotations

from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any

from app.backend.sqlite_store import find_similar_artefacts


@dataclass(frozen=True)
class ArtifactReuseDecision:
    reused_artifacts: list[dict[str, Any]] = field(default_factory=list)
    missing_artifact_types: list[str] = field(default_factory=list)


class ArtifactReuseAgent:
    """Searches persisted artifacts and decides what can be reused."""

    def __init__(self, *, similarity_threshold: float = 0.72):
        self.similarity_threshold = similarity_threshold

    def find_reusable_artifacts(
        self,
        *,
        project: str,
        user_input: str,
        artifact_types: list[str],
        desired_counts: dict[str, int] | None = None,
    ) -> ArtifactReuseDecision:
        desired_counts = desired_counts or {}
        reused: list[dict[str, Any]] = []
        missing: list[str] = []

        for artifact_type in artifact_types:
            candidates = find_similar_artefacts(
                project=project,
                artifact_type=artifact_type,
                query=user_input,
                limit=10,
            )
            matches = [
                artifact
                for artifact in candidates
                if self._is_reusable(artifact=artifact, user_input=user_input)
            ]
            if matches:
                reused.extend(matches)
            if len(matches) < max(1, desired_counts.get(artifact_type, 1)):
                missing.append(artifact_type)

        return ArtifactReuseDecision(
            reused_artifacts=self._dedupe(reused),
            missing_artifact_types=missing,
        )

    def _is_reusable(self, *, artifact: dict[str, Any], user_input: str) -> bool:
        title = str(artifact.get("title") or "")
        content = str(artifact.get("content") or "")
        haystack = f"{title} {content}".lower()
        needle = user_input.lower().strip()

        if not needle:
            return False

        if needle in haystack or title.lower() in needle:
            return True

        return SequenceMatcher(None, needle, haystack[: max(len(needle) * 2, 120)]).ratio() >= self.similarity_threshold

    @staticmethod
    def _dedupe(artifacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        deduped: list[dict[str, Any]] = []
        seen: set[tuple[Any, str, str]] = set()
        for artifact in artifacts:
            key = (
                artifact.get("id"),
                str(artifact.get("title") or ""),
                str(artifact.get("content") or ""),
            )
            if key in seen:
                continue
            seen.add(key)
            deduped.append(artifact)
        return deduped


artifact_reuse_agent = ArtifactReuseAgent()
