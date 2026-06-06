"""
Base class for all artifact generation agents.
This provides a standardized interface for all artifact generators.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List
from dataclasses import dataclass
from app.backend.subagent_coordinator import ArtifactResult, ArtifactType


@dataclass
class ArtifactGenerationContext:
    """Context information for artifact generation."""
    user_input: str
    context_content: str
    related_artifacts: List[Dict[str, Any]]
    target_audience: str
    session_id: str


class BaseArtifactGenerator(ABC):
    """Abstract base class for all artifact generators."""
    
    def __init__(self, artifact_type: ArtifactType):
        self.artifact_type = artifact_type
    
    @abstractmethod
    def generate(self, context: ArtifactGenerationContext, backend) -> ArtifactResult:
        """Generate the artifact based on the given context."""
        pass
    
    def validate_result(self, result: ArtifactResult) -> bool:
        """Validate that the generated artifact meets quality standards."""
        # Basic validation - can be overridden by specific implementations
        return (
            result is not None and
            result.artifact_type == self.artifact_type and
            result.content is not None and
            len(result.content.strip()) > 0
        )
    
    def get_metadata(self, context: ArtifactGenerationContext) -> Dict[str, Any]:
        """Get metadata about the generation process."""
        return {
            "artifact_type": self.artifact_type.value,
            "target_audience": context.target_audience,
            "session_id": context.session_id,
            "generation_method": "llm_based"
        }