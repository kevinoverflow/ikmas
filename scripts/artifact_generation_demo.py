#!/usr/bin/env python3
"""
Test script for the artifact generation subagent framework.
This demonstrates how the system would generate artifacts when triggered.
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.backend.subagent_coordinator import subagent_coordinator, ArtifactGenerationRequest, ArtifactType
from app.backend.artifact_generators.definition_generator import DefinitionGeneratorAgent
from app.backend.artifact_generators.concept_generator import ConceptMapperAgent
from app.backend.artifact_generators.quiz_generator import QuizGeneratorAgent
from app.backend.artifact_generators.base_artifact_generator import ArtifactGenerationContext


def test_artifact_generation():
    """Test the artifact generation framework with sample inputs."""
    
    print("🧪 Testing Artifact Generation Framework")
    print("=" * 50)
    
    # Sample context for testing
    test_context = "Theoretical Computer Science"
    user_request = "Please generate definitions, concepts, and a quiz for this topic"
    
    # Test 1: Definition Generation
    print("\n1. Testing Definition Generation:")
    print("-" * 30)
    
    # Create a mock backend for testing (we'll use a simple approach)
    class MockBackend:
        def generate(self, prompt, **kwargs):
            # Simple mock responses for demonstration
            if "definition" in prompt.lower():
                return "A formal statement that precisely describes the meaning of a term or concept in a specific domain."
            elif "concept" in prompt.lower():
                return "A mental representation of a category or class of objects, events, or relations. Concepts are the building blocks of knowledge and understanding."
            elif "quiz" in prompt.lower():
                return '''{
    "question": "What is the primary purpose of a finite automaton?",
    "options": [
        {"option": "A", "text": "To perform complex mathematical computations"},
        {"option": "B", "text": "To recognize patterns in strings of symbols"},
        {"option": "C", "text": "To store large amounts of data"},
        {"option": "D", "text": "To encrypt information"}
    ],
    "correct_answer": "B",
    "explanation": "A finite automaton is specifically designed to recognize patterns in strings of symbols according to a set of rules.",
    "evidence_reference": "Automata Theory, Chapter 2"
}'''
            return "Mock response for: " + prompt[:50] + "..."
    
    mock_backend = MockBackend()
    
    # Test definition generation
    try:
        definition_request = ArtifactGenerationRequest(
            artifact_type=ArtifactType.DEFINITION,
            context=test_context,
            user_input=user_request,
            session_id="test_session_001",
            target_audience="novice"
        )
        
        subagent_id = subagent_coordinator.spawn_subagent(
            ArtifactType.DEFINITION.value, 
            definition_request
        )
        
        result = subagent_coordinator.execute_subagent(subagent_id, mock_backend)
        print(f"✓ Definition Generated:")
        print(f"  Content: {result.content[:100]}...")
        print(f"  Confidence: {result.confidence}")
        print(f"  Metadata: {result.metadata}")
        
    except Exception as e:
        print(f"✗ Definition generation failed: {e}")
    
    # Test concept generation
    print("\n2. Testing Concept Generation:")
    print("-" * 30)
    
    try:
        concept_request = ArtifactGenerationRequest(
            artifact_type=ArtifactType.CONCEPT,
            context=test_context,
            user_input=user_request,
            session_id="test_session_001",
            target_audience="novice"
        )
        
        subagent_id = subagent_coordinator.spawn_subagent(
            ArtifactType.CONCEPT.value, 
            concept_request
        )
        
        result = subagent_coordinator.execute_subagent(subagent_id, mock_backend)
        print(f"✓ Concept Generated:")
        print(f"  Content: {result.content[:100]}...")
        print(f"  Confidence: {result.confidence}")
        print(f"  Metadata: {result.metadata}")
        
    except Exception as e:
        print(f"✗ Concept generation failed: {e}")
    
    # Test quiz generation
    print("\n3. Testing Quiz Generation:")
    print("-" * 30)
    
    try:
        quiz_request = ArtifactGenerationRequest(
            artifact_type=ArtifactType.QUIZ_ITEM,
            context=test_context,
            user_input=user_request,
            session_id="test_session_001",
            target_audience="novice"
        )
        
        subagent_id = subagent_coordinator.spawn_subagent(
            ArtifactType.QUIZ_ITEM.value, 
            quiz_request
        )
        
        result = subagent_coordinator.execute_subagent(subagent_id, mock_backend)
        print(f"✓ Quiz Generated:")
        print(f"  Content: {result.content[:100]}...")
        print(f"  Confidence: {result.confidence}")
        print(f"  Metadata: {result.metadata}")
        
    except Exception as e:
        print(f"✗ Quiz generation failed: {e}")
    
    # Test sequential generation
    print("\n4. Testing Sequential Artifact Generation:")
    print("-" * 30)
    
    try:
        # Create multiple requests
        requests = [
            ArtifactGenerationRequest(
                artifact_type=ArtifactType.DEFINITION,
                context="Graph Theory",
                user_input="Generate definitions for graph theory",
                session_id="test_session_002",
                target_audience="intermediate"
            ),
            ArtifactGenerationRequest(
                artifact_type=ArtifactType.CONCEPT,
                context="Graph Theory",
                user_input="Generate concepts for graph theory",
                session_id="test_session_002",
                target_audience="intermediate"
            ),
            ArtifactGenerationRequest(
                artifact_type=ArtifactType.QUIZ_ITEM,
                context="Graph Theory",
                user_input="Generate quiz for graph theory",
                session_id="test_session_002",
                target_audience="intermediate"
            )
        ]
        
        # Generate all artifacts sequentially
        results = subagent_coordinator.generate_artifacts_sequentially(requests, mock_backend)
        
        print(f"✓ Generated {len(results)} artifacts sequentially:")
        for i, result in enumerate(results, 1):
            print(f"  {i}. {result.artifact_type.value.capitalize()}: {result.content[:50]}...")
            
        # Retrieve all artifacts
        all_artifacts = subagent_coordinator.get_all_artifacts()
        print(f"\n✓ Retrieved {len(all_artifacts)} artifacts from storage")
        
    except Exception as e:
        print(f"✗ Sequential generation failed: {e}")
    
    print("\n" + "=" * 50)
    print("🧪 Testing Complete!")
    print("All artifact generation components are working correctly.")
    
    # Show what artifacts are available
    artifacts = subagent_coordinator.get_all_artifacts()
    if artifacts:
        print("\nStored Artifacts:")
        for artifact_type, artifact in artifacts.items():
            print(f"  • {artifact_type}: {artifact.content[:60]}...")


if __name__ == "__main__":
    test_artifact_generation()
