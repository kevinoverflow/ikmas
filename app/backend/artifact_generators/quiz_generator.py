"""
Quiz Item Generator Agent for creating assessment questions and answers.
"""

from typing import Dict, Any, List
from app.backend.artifact_generators.base_artifact_generator import BaseArtifactGenerator, ArtifactGenerationContext
from app.backend.subagent_coordinator import ArtifactResult, ArtifactType
from app.infrastructure.tracing import traceable


class QuizGeneratorAgent(BaseArtifactGenerator):
    """Generates quiz items with questions, answers, and evidence references."""
    
    def __init__(self):
        super().__init__(ArtifactType.QUIZ_ITEM)
    
    @traceable(name="quiz_generator_generate", run_type="llm")
    def generate(self, context: ArtifactGenerationContext, backend) -> ArtifactResult:
        """Generate a quiz item (question + answer + evidence)."""
        
        # Create a prompt for the LLM to generate a quiz item
        prompt = f"""
        Create a quiz item for assessing understanding of the following topic:

        Topic: "{context.context_content}"

        User's original request: "{context.user_input}"

        Target audience: {context.target_audience}

        Requirements:
        1. Create a clear, unambiguous multiple choice question
        2. Provide one correct answer and three plausible distractors
        3. Include a brief explanation of why the correct answer is right
        4. Reference specific evidence or source material that supports the answer
        5. Ensure the question tests understanding rather than mere memorization
        6. Keep the question focused on key concepts

        Format the response as a structured quiz item:
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

        Quiz Item:
        """
        
        # Generate using the backend
        raw_response = backend.generate(
            prompt,
            temperature=0.3,  # Low temperature for consistency
            max_tokens=400,
            response_format={"type": "json_object"}
        )
        
        # For now, we'll treat the raw response as a simple text representation
        # In a real implementation, we'd parse the JSON properly
        quiz_content = raw_response.strip()
        
        # Extract key metadata
        metadata = self.get_metadata(context)
        metadata.update({
            "audience_level": context.target_audience,
            "item_type": "multiple_choice"
        })
        
        return ArtifactResult(
            artifact_type=self.artifact_type,
            content=quiz_content,
            metadata=metadata,
            confidence=0.80  # Good confidence for quiz generation
        )