from app.backend.artifact_generators.base_artifact_generator import ArtifactGenerationContext
from app.backend.artifact_generators.concept_generator import (
    ConceptMapperAgent,
    estimate_concept_count,
)
from app.backend.artifact_generators.definition_generator import (
    DefinitionGeneratorAgent,
    estimate_definition_count,
)


def test_estimate_definition_count_scales_with_context_size():
    assert estimate_definition_count("short context") == 1
    assert estimate_definition_count("word " * 90) == 2
    assert estimate_definition_count("word " * 220) == 3
    assert estimate_definition_count("word " * 400) == 4
    assert estimate_definition_count("word " * 800) == 5


def test_estimate_concept_count_scales_with_context_size():
    assert estimate_concept_count("short context") == 1
    assert estimate_concept_count("word " * 150) == 2
    assert estimate_concept_count("word " * 400) == 3
    assert estimate_concept_count("word " * 800) == 4


def test_definition_generator_requests_multiple_definitions_for_larger_context():
    seen = {}

    class FakeBackend:
        def generate(self, prompt, **kwargs):
            seen["prompt"] = prompt
            seen["kwargs"] = kwargs
            return '{"definitions": []}'

    context = ArtifactGenerationContext(
        user_input="Generate definitions",
        context_content="word " * 220,
        related_artifacts=[],
        target_audience="novice",
        session_id="session-1",
    )

    result = DefinitionGeneratorAgent().generate(context, FakeBackend())

    assert "Generate up to 3 formal" in seen["prompt"]
    assert seen["kwargs"]["max_tokens"] == 660
    assert result.metadata["requested_item_count"] == 3


def test_concept_generator_requests_multiple_concepts_for_larger_context():
    seen = {}

    class FakeBackend:
        def generate(self, prompt, **kwargs):
            seen["prompt"] = prompt
            seen["kwargs"] = kwargs
            return '{"concepts": []}'

    context = ArtifactGenerationContext(
        user_input="Generate concepts",
        context_content="word " * 400,
        related_artifacts=[],
        target_audience="novice",
        session_id="session-1",
    )

    result = ConceptMapperAgent().generate(context, FakeBackend())

    assert "Create up to 3 conceptual" in seen["prompt"]
    assert seen["kwargs"]["max_tokens"] == 960
    assert result.metadata["requested_item_count"] == 3
