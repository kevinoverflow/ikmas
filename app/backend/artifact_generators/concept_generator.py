"""
Concept Generator Agent for creating conceptual explanations and mappings.
"""

from typing import Dict, Any, List
from app.backend.artifact_generators.base_artifact_generator import BaseArtifactGenerator, ArtifactGenerationContext
from app.backend.subagent_coordinator import ArtifactResult, ArtifactType
from app.infrastructure.tracing import traceable


class ConceptMapperAgent(BaseArtifactGenerator):
    """Generates conceptual explanations and maps relationships between ideas."""
    
    def __init__(self):
        super().__init__(ArtifactType.CONCEPT)
    
    @traceable(name="concept_mapper_generate", run_type="llm")
    def generate(self, context: ArtifactGenerationContext, backend) -> ArtifactResult:
        """Generate a conceptual explanation and mapping."""
        
        # Create a prompt for the LLM to generate a concept explanation
        prompt = f"""
        Create a comprehensive conceptual explanation for the following topic:

        Topic: "{context.context_content}"

        User's original request: "{context.user_input}"

        Target audience: {context.target_audience}

        Requirements:
        1. Explain the core concept in accessible terms
        2. Describe the key characteristics and properties
        3. Explain how it relates to related concepts
        4. Provide intuitive examples or analogies
        5. Highlight important distinctions from similar concepts
        6. Mention practical applications or significance

        Format the response as a structured conceptual explanation with:
        - Core definition of the concept
        - Key characteristics and properties
        - Relationships to related concepts
        - Examples or analogies
        - Practical significance

        Concept Explanation:
        """
        
        # Generate using the backend
        raw_response = backend.generate(
            prompt,
            temperature=0.4,  # Slightly higher temperature for creativity
            max_tokens=600
        )
        
        # Validate and structure the result
        concept_explanation = raw_response.strip()
        
        # Extract key metadata
        metadata = self.get_metadata(context)
        metadata.update({
            "word_count": len(concept_explanation.split()),
            "audience_level": context.target_audience
        })
        
        return ArtifactResult(
            artifact_type=self.artifact_type,
            content=concept_explanation,
            metadata=metadata,
            confidence=0.85  # Good confidence for conceptual explanations
        )