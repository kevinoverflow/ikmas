from app.backend.artifact_generators.base_artifact_generator import ArtifactGenerationContext
from app.backend.artifact_generators.quiz_generator import (
    QuizGeneratorAgent,
    estimate_quiz_item_count,
)


def test_estimate_quiz_item_count_scales_with_context_size():
    assert estimate_quiz_item_count("short context") == 1
    assert estimate_quiz_item_count("word " * 90) == 2
    assert estimate_quiz_item_count("word " * 220) == 3
    assert estimate_quiz_item_count("word " * 400) == 4
    assert estimate_quiz_item_count("word " * 800) == 5


def test_quiz_generator_requests_multiple_items_for_larger_context():
    seen = {}

    class FakeBackend:
        def generate(self, prompt, **kwargs):
            seen["prompt"] = prompt
            seen["kwargs"] = kwargs
            return '{"quiz_items": []}'

    context = ArtifactGenerationContext(
        user_input="Make a quiz",
        context_content="word " * 220,
        related_artifacts=[],
        target_audience="novice",
        session_id="session-1",
    )

    result = QuizGeneratorAgent().generate(context, FakeBackend())

    assert "Create 3 quiz item(s)" in seen["prompt"]
    assert seen["kwargs"]["max_tokens"] == 1050
    assert result.metadata["requested_item_count"] == 3
