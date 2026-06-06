"""
Definition Generator Agent for creating formal definitions of concepts.
"""

from typing import Dict, Any, List
from app.backend.artifact_generators.base_artifact_generator import BaseArtifactGenerator, ArtifactGenerationContext
from app.backend.subagent_coordinator import ArtifactResult, ArtifactType
from app.infrastructure.tracing import traceable


class DefinitionGeneratorAgent(BaseArtifactGenerator):
    """Generates formal, precise definitions of concepts and terms."""
    
    def __init__(self):
        super().__init__(ArtifactType.DEFINITION)
    
    @traceable(name="definition_generator_generate", run_type="llm")
    def generate(self, context: ArtifactGenerationContext, backend) -> ArtifactResult:
        """Generate a formal definition based on the context."""
        
        # Create a prompt for the LLM to generate a definition
        prompt = f"""
        Generate a formal, precise definition for the following concept or term:

        Concept/Topic: "{context.context_content}"

        User's original request: "{context.user_input}"

        Target audience: {context.target_audience}

        Requirements:
        1. Provide a clear, concise definition that captures the essential meaning
        2. Use precise academic language appropriate for the target audience
        3. Include any necessary qualifiers or constraints that define the scope
        4. Reference related concepts if relevant
        5. Keep the definition focused on the core meaning

        Format the response as a well-structured definition with:
        - Clear statement of what the concept means
        - Any important distinctions or limitations
        - Connection to related ideas if applicable

        Definition:
        """
        
        # Generate using the backend
        raw_response = backend.generate(
            prompt,
            temperature=0.3,  # Low temperature for consistency
            max_tokens=500
        )
        
        # Validate and structure the result
        definition = raw_response.strip()
        
        # Extract key metadata
        metadata = self.get_metadata(context)
        metadata.update({
            "word_count": len(definition.split()),
            "audience_level": context.target_audience
        })
        
        return ArtifactResult(
            artifact_type=self.artifact_type,
            content=definition,
            metadata=metadata,
            confidence=0.90  # High confidence for definition generation
        )