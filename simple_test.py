#!/usr/bin/env python3
"""
Simple test for the artifact generation framework.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from app.backend.subagent_coordinator import subagent_coordinator, ArtifactGenerationRequest, ArtifactType


def test_simple():
    """Simple test of the core functionality."""
    
    print("🧪 Simple Artifact Generation Test")
    print("=" * 40)
    
    # Create a mock backend for testing
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
    
    # Test 1: Single artifact generation
    print("\n1. Testing Single Artifact Generation:")
    print("-" * 35)
    
    try:
        # Create a definition request
        definition_request = ArtifactGenerationRequest(
            artifact_type=ArtifactType.DEFINITION,
            context="Graph Theory",
            user_input="Generate a definition for Graph Theory",
            session_id="test_session_001",
            target_audience="novice"
        )
        
        # Spawn subagent
        subagent_id = subagent_coordinator.spawn_subagent(
            ArtifactType.DEFINITION.value, 
            definition_request
        )
        print(f"✓ Subagent spawned with ID: {subagent_id}")
        
        # Execute subagent
        result = subagent_coordinator.execute_subagent(subagent_id, mock_backend)
        print(f"✓ Definition Generated successfully!")
        print(f"  Type: {result.artifact_type}")
        print(f"  Content preview: {result.content[:80]}...")
        print(f"  Confidence: {result.confidence}")
        
    except Exception as e:
        print(f"✗ Single generation failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 2: Check stored artifacts
    print("\n2. Checking Stored Artifacts:")
    print("-" * 35)
    
    try:
        artifacts = subagent_coordinator.get_all_artifacts()
        print(f"✓ Found {len(artifacts)} stored artifacts")
        for artifact_type, artifact in artifacts.items():
            print(f"  • {artifact_type}: {artifact.content[:50]}...")
            
    except Exception as e:
        print(f"✗ Artifact retrieval failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 40)
    print("🧪 Simple Test Complete!")


if __name__ == "__main__":
    test_simple()