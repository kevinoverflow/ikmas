"""
Quiz Item Generator Agent for creating assessment questions and answers.
"""

from app.backend.artifact_generators.base_artifact_generator import BaseArtifactGenerator, ArtifactGenerationContext
from app.backend.artifact_models import ArtifactResult, ArtifactType
from app.infrastructure.tracing import traceable


def estimate_quiz_item_count(context_content: str) -> int:
    """Estimate how many quiz items the available knowledge can support."""
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


class QuizGeneratorAgent(BaseArtifactGenerator):
    """Generates quiz items with questions, answers, and evidence references."""
    
    def __init__(self):
        super().__init__(ArtifactType.QUIZ_ITEM)
    
    @traceable(name="quiz_generator_generate", run_type="llm")
    def generate(self, context: ArtifactGenerationContext, backend) -> ArtifactResult:
        """Generate one or more quiz items (question + answer + evidence)."""
        item_count = estimate_quiz_item_count(context.context_content)
        existing_artifacts = "\n".join(
            f"- {artifact.get('title', 'Untitled')}: {artifact.get('content', '')[:240]}"
            for artifact in context.related_artifacts
            if artifact.get("type") == ArtifactType.QUIZ_ITEM.value
        ) or "None"
        
        prompt = f"""
        Create {item_count} quiz item(s) for assessing understanding of the following knowledge.
        Use fewer only if the source content genuinely cannot support {item_count} distinct questions.

        Knowledge:
        "{context.context_content}"

        User's original request: "{context.user_input}"

        Target audience: {context.target_audience}

        Existing quiz artifacts already available:
        {existing_artifacts}

        Requirements:
        1. Create clear, unambiguous multiple choice questions
        2. Provide one correct answer and three plausible distractors per question
        3. Include a brief explanation of why the correct answer is right
        4. Reference specific evidence or source material that supports the answer
        5. Ensure each question tests understanding rather than mere memorization
        6. Cover distinct concepts or facts when multiple quiz items are requested
        7. Do not invent source evidence that is not supported by the knowledge above
        8. Do not recreate quiz items that are already covered by existing artifacts

        Return only valid JSON with this exact structure:
        {{
          "quiz_items": [
            {{
              "question": "The actual question text",
              "options": [
                {{ "option": "A", "text": "First option" }},
                {{ "option": "B", "text": "Second option" }},
                {{ "option": "C", "text": "Third option" }},
                {{ "option": "D", "text": "Correct answer" }}
              ],
              "correct_answer": "D",
              "explanation": "Brief explanation of why the correct answer is right",
              "evidence_reference": "Reference to source material or concept that supports this"
            }}
          ]
        }}
        """
        
        raw_response = backend.generate(
            prompt,
            temperature=0.3,
            max_tokens=350 * item_count,
            response_format={"type": "json_object"}
        )
        
        quiz_content = raw_response.strip()
        
        metadata = self.get_metadata(context)
        metadata.update({
            "audience_level": context.target_audience,
            "item_type": "multiple_choice",
            "requested_item_count": item_count,
        })
        
        return ArtifactResult(
            artifact_type=self.artifact_type,
            content=quiz_content,
            metadata=metadata,
            confidence=0.80  # Good confidence for quiz generation
        )
