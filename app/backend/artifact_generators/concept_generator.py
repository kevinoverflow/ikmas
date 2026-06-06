"""
Concept Generator Agent for creating conceptual explanations and mappings.
"""

from app.backend.artifact_generators.base_artifact_generator import BaseArtifactGenerator, ArtifactGenerationContext
from app.backend.artifact_models import ArtifactResult, ArtifactType
from app.infrastructure.tracing import traceable


def estimate_concept_count(context_content: str) -> int:
    """Estimate how many concept cards the available knowledge can support."""
    word_count = len(context_content.split())
    if word_count >= 700:
        return 4
    if word_count >= 350:
        return 3
    if word_count >= 120:
        return 2
    return 1


class ConceptMapperAgent(BaseArtifactGenerator):
    """Generates conceptual explanations and maps relationships between ideas."""
    
    def __init__(self):
        super().__init__(ArtifactType.CONCEPT)
    
    @traceable(name="concept_mapper_generate", run_type="llm")
    def generate(self, context: ArtifactGenerationContext, backend) -> ArtifactResult:
        """Generate one or more conceptual explanations and mappings."""
        concept_count = estimate_concept_count(context.context_content)
        existing_artifacts = "\n".join(
            f"- {artifact.get('title', 'Untitled')}: {artifact.get('content', '')[:240]}"
            for artifact in context.related_artifacts
            if artifact.get("type") == ArtifactType.CONCEPT.value
        ) or "None"
        
        prompt = f"""
        Create up to {concept_count} conceptual explanation card(s) from the following knowledge.
        Use fewer only if the source content cannot support {concept_count} distinct concept cards.

        Knowledge:
        "{context.context_content}"

        User's original request: "{context.user_input}"

        Target audience: {context.target_audience}

        Existing concept artifacts already available:
        {existing_artifacts}

        Requirements:
        1. Identify distinct core concepts when multiple cards are useful
        2. Explain each core concept in accessible terms
        2. Describe the key characteristics and properties
        3. Explain how it relates to related concepts
        4. Provide intuitive examples or analogies
        5. Highlight important distinctions from similar concepts
        6. Mention practical applications or significance
        7. Do not invent concepts that are not supported by the knowledge above
        8. Do not recreate concept cards that are already covered by existing artifacts

        Return only valid JSON with this exact structure:
        {{
          "concepts": [
            {{
              "title": "Concept name",
              "explanation": "Accessible conceptual explanation",
              "relationships": "Important relationships to other concepts",
              "example": "Short practical example or analogy"
            }}
          ]
        }}
        """
        
        raw_response = backend.generate(
            prompt,
            temperature=0.4,
            max_tokens=320 * concept_count,
            response_format={"type": "json_object"},
        )
        
        concept_explanation = raw_response.strip()
        
        metadata = self.get_metadata(context)
        metadata.update({
            "word_count": len(concept_explanation.split()),
            "audience_level": context.target_audience,
            "requested_item_count": concept_count,
        })
        
        return ArtifactResult(
            artifact_type=self.artifact_type,
            content=concept_explanation,
            metadata=metadata,
            confidence=0.85  # Good confidence for conceptual explanations
        )
