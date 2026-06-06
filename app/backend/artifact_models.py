"""
Shared models for artifact generation.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List


class ArtifactType(str, Enum):
    """Types of knowledge artifacts that can be generated."""

    DEFINITION = "definition"
    CONCEPT = "concept"
    PREREQUISITE = "prerequisite"
    PITFALL = "pitfall"
    CASE = "case"
    QUIZ_ITEM = "quiz_item"


@dataclass
class ArtifactGenerationRequest:
    """Request for generating a specific type of artifact."""

    artifact_type: ArtifactType
    context: str
    user_input: str
    session_id: str
    related_artifacts: List[Dict[str, Any]] | None = None
    target_audience: str = "general"


@dataclass
class ArtifactResult:
    """Result from artifact generation."""

    artifact_type: ArtifactType
    content: str
    metadata: Dict[str, Any]
    confidence: float = 0.0
    generated_at: str | None = None
    source_artifacts: List[str] | None = None
