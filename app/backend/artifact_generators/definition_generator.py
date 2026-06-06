"""
Definition Generator Agent for creating formal definitions of concepts.
"""

from app.backend.artifact_generators.base_artifact_generator import BaseArtifactGenerator, ArtifactGenerationContext
from app.backend.artifact_models import ArtifactResult, ArtifactType
from app.infrastructure.tracing import traceable


def estimate_definition_count(context_content: str) -> int:
    """Estimate how many distinct definitions the available knowledge can support."""
    word_count = len(context_content.split())
    if word_count >= 700:
        return 5
    if word_count >= 350:
        return 4
    if word_count >= 180:
        return 3
    if word_count >= 80:
        return 2
    return 1


class DefinitionGeneratorAgent(BaseArtifactGenerator):
    """Generates formal, precise definitions of concepts and terms."""
    
    def __init__(self):
        super().__init__(ArtifactType.DEFINITION)
    
    @traceable(name="definition_generator_generate", run_type="llm")
    def generate(self, context: ArtifactGenerationContext, backend) -> ArtifactResult:
        """Generate one or more formal definitions based on the context."""
        definition_count = estimate_definition_count(context.context_content)
        existing_artifacts = "\n".join(
            f"- {artifact.get('title', 'Untitled')}: {artifact.get('content', '')[:240]}"
            for artifact in context.related_artifacts
            if artifact.get("type") == ArtifactType.DEFINITION.value
        ) or "None"
        
        prompt = f"""
        Generate up to {definition_count} formal, precise definition(s) from the following knowledge.
        Use fewer only if the source content cannot support {definition_count} distinct definitions.

        Knowledge:
        "{context.context_content}"

        User's original request: "{context.user_input}"

        Target audience: {context.target_audience}

        Existing definition artifacts already available:
        {existing_artifacts}

        Requirements:
        1. Identify distinct concepts or terms worth defining
        2. Provide clear, concise definitions that capture essential meaning
        2. Use precise academic language appropriate for the target audience
        3. Include any necessary qualifiers or constraints that define the scope
        4. Reference related concepts if relevant
        5. Keep each definition focused on one core meaning
        6. Do not invent concepts that are not supported by the knowledge above
        7. Do not recreate definitions that are already covered by existing artifacts

        Return only valid JSON with this exact structure:
        {{
          "definitions": [
            {{
              "title": "Concept or term name",
              "definition": "Clear definition text",
              "scope": "Important limits, qualifiers, or related distinctions"
            }}
          ]
        }}
        """
        
        raw_response = backend.generate(
            prompt,
            temperature=0.3,
            max_tokens=220 * definition_count,
            response_format={"type": "json_object"},
        )
        
        definition = raw_response.strip()
        
        metadata = self.get_metadata(context)
        metadata.update({
            "word_count": len(definition.split()),
            "audience_level": context.target_audience,
            "requested_item_count": definition_count,
        })
        
        return ArtifactResult(
            artifact_type=self.artifact_type,
            content=definition,
            metadata=metadata,
            confidence=0.90  # High confidence for definition generation
        )
