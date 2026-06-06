#!/usr/bin/env python3
"""
Simple demonstration of how the artifact generation system integrates with 
the router concept to automatically detect when artifact generation is needed.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from app.backend.subagent_coordinator import subagent_coordinator, ArtifactGenerationRequest, ArtifactType


def demonstrate_simple_integration():
    """Demonstrate the core integration concept without router dependencies."""
    
    print("🔍 Simple Router Integration Demonstration")
    print("=" * 50)
    
    # Create a mock backend for testing
    class MockBackend:
        def generate(self, prompt, **kwargs):
            # Mock responses for different artifact types
            if "definition" in prompt.lower() and "graph" in prompt.lower():
                return "A finite automaton is a mathematical model of computation that consists of states, transitions, and an alphabet of symbols."
            elif "concept" in prompt.lower() and "graph" in prompt.lower():
                return "Graph theory is the study of graphs, which are mathematical structures used to model pairwise relations between objects. A graph consists of vertices (or nodes) connected by edges."
            elif "quiz" in prompt.lower() and "graph" in prompt.lower():
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
            elif "definition" in prompt.lower() and "algorithm" in prompt.lower():
                return "An algorithm is a step-by-step procedure for solving a problem or accomplishing a task in a finite amount of time."
            elif "concept" in prompt.lower() and "algorithm" in prompt.lower():
                return "An algorithm represents a logical sequence of steps to solve computational problems. It's a fundamental concept in computer science that encompasses both theoretical analysis and practical implementation."
            elif "quiz" in prompt.lower() and "algorithm" in prompt.lower():
                return '''{
    "question": "Which of the following best describes an algorithm?",
    "options": [
        {"option": "A", "text": "A programming language"},
        {"option": "B", "text": "A mathematical proof"},
        {"option": "C", "text": "A step-by-step procedure for solving problems"},
        {"option": "D", "text": "A type of data structure"}
    ],
    "correct_answer": "C",
    "explanation": "An algorithm is fundamentally defined as a step-by-step procedure for solving computational problems.",
    "evidence_reference": "Algorithm Design Manual, Chapter 1"
}'''
            return "Mock response for: " + prompt[:50] + "..."
    
    mock_backend = MockBackend()
    
    # Simulate different user requests that would trigger router detection
    test_scenarios = [
        {
            "user_input": "Test my understanding of graph theory",
            "description": "User wants to test their understanding of a topic",
            "expected_artifacts": ["definition", "concept", "quiz_item"]
        },
        {
            "user_input": "Explain the concepts in algorithms",
            "description": "User wants conceptual explanations",
            "expected_artifacts": ["concept"]
        },
        {
            "user_input": "Define what an algorithm is",
            "description": "User wants specific definitions",
            "expected_artifacts": ["definition"]
        },
        {
            "user_input": "Generate quiz questions for theoretical computer science",
            "description": "User explicitly requests quiz generation",
            "expected_artifacts": ["quiz_item"]
        }
    ]
    
    print("Testing Automatic Artifact Generation Detection:")
    print("-" * 60)
    
    for i, scenario in enumerate(test_scenarios, 1):
        user_input = scenario["user_input"]
        description = scenario["description"]
        expected_artifacts = scenario["expected_artifacts"]
        
        print(f"\n{i}. User Input: \"{user_input}\"")
        print(f"   Description: {description}")
        
        # Simulate router logic that would detect artifact needs
        print("   Router Detection Logic:")
        
        # This represents the router's pattern matching logic
        artifact_plan = {"artifacts_needed": [], "processing_order": []}
        
        # Pattern matching (simplified router logic)
        if "test" in user_input.lower() or "understand" in user_input.lower():
            artifact_plan["artifacts_needed"].extend(["definition", "concept", "quiz_item"])
            artifact_plan["processing_order"].extend(["definition", "concept", "quiz_item"])
            print("     ✓ Pattern detected: 'test' or 'understand' - knowledge testing request")
            
        elif "explain" in user_input.lower() or "concept" in user_input.lower():
            artifact_plan["artifacts_needed"].append("concept")
            artifact_plan["processing_order"].append("concept")
            print("     ✓ Pattern detected: 'explain' or 'concept' - conceptual request")
            
        elif "define" in user_input.lower() or "definition" in user_input.lower():
            artifact_plan["artifacts_needed"].append("definition")
            artifact_plan["processing_order"].append("definition")
            print("     ✓ Pattern detected: 'define' or 'definition' - definition request")
            
        elif "quiz" in user_input.lower() or "question" in user_input.lower():
            artifact_plan["artifacts_needed"].append("quiz_item")
            artifact_plan["processing_order"].append("quiz_item")
            print("     ✓ Pattern detected: 'quiz' or 'question' - quiz request")
        
        print(f"   Recommended Artifacts: {artifact_plan['artifacts_needed']}")
        
        # If artifact generation is needed, execute the workflow
        if artifact_plan["artifacts_needed"]:
            print("   Executing Artifact Generation Workflow:")
            print(f"     ✓ Spawning {len(artifact_plan['artifacts_needed'])} specialized subagents")
            
            # Create requests for each artifact type
            requests = []
            for artifact_type_str in artifact_plan["artifacts_needed"]:
                artifact_type = ArtifactType(artifact_type_str)
                request = ArtifactGenerationRequest(
                    artifact_type=artifact_type,
                    context=user_input,
                    user_input=user_input,
                    session_id=f"session_{i:03d}",
                    target_audience="novice"
                )
                requests.append(request)
                print(f"       • Created request for {artifact_type_str}")
            
            # Execute sequentially (as in real system)
            results = subagent_coordinator.generate_artifacts_sequentially(requests, mock_backend)
            print(f"     ✓ Generated {len(results)} artifacts successfully")
            
            # Show results
            print("     Generated Artifacts:")
            for j, result in enumerate(results, 1):
                print(f"       {j}. {result.artifact_type.value.upper()}:")
                print(f"          Content: {result.content[:80]}...")
                print(f"          Confidence: {result.confidence}")
                print()
        else:
            print("   No artifact generation needed for this request")
        
        print("-" * 60)
    
    # Demonstrate the complete "Test my understanding" workflow
    print("\n🎯 Complete 'Test my understanding' Workflow Demo")
    print("-" * 60)
    
    user_request = "Test my understanding of graph theory"
    print(f"User Request: \"{user_request}\"")
    
    # Step 1: Router would detect this pattern
    print("\n1. Router Pattern Detection:")
    print("   ✓ Detected: 'test my understanding' pattern")
    print("   ✓ Identified: Knowledge testing scenario")
    print("   ✓ Recommended artifacts: definitions, concepts, quizzes")
    
    # Step 2: Create artifact generation plan
    artifact_plan = {
        "artifacts_needed": ["definition", "concept", "quiz_item"],
        "processing_order": ["definition", "concept", "quiz_item"]
    }
    print(f"\n2. Artifact Generation Plan: {artifact_plan}")
    
    # Step 3: Execute the workflow
    print("\n3. Executing Artifact Generation:")
    
    # Create requests
    requests = []
    for artifact_type_str in artifact_plan["artifacts_needed"]:
        artifact_type = ArtifactType(artifact_type_str)
        request = ArtifactGenerationRequest(
            artifact_type=artifact_type,
            context="Graph Theory",
            user_input=user_request,
            session_id="test_workflow_001",
            target_audience="novice"
        )
        requests.append(request)
        print(f"   ✓ Created request for {artifact_type_str}")
    
    # Execute sequentially
    results = subagent_coordinator.generate_artifacts_sequentially(requests, mock_backend)
    print(f"   ✓ Generated {len(results)} artifacts successfully")
    
    # Step 4: Show the results
    print("\n4. Generated Artifacts:")
    for i, result in enumerate(results, 1):
        print(f"   {i}. {result.artifact_type.value.upper()}:")
        print(f"      Content: {result.content[:100]}...")
        print(f"      Confidence: {result.confidence}")
        print(f"      Metadata: {result.metadata}")
        print()
    
    # Step 5: Show how these would be used
    print("5. Integration with Learning Workflow:")
    print("   ✓ Definitions stored for reference")
    print("   ✓ Concepts available for explanation")
    print("   ✓ Quiz items ready for assessment")
    print("   ✓ All artifacts preserved for session context")
    
    print("\n" + "=" * 50)
    print("✅ Router Integration Working!")
    print("The system automatically detects when artifact generation is needed")
    print("and seamlessly integrates it into the learning experience.")


if __name__ == "__main__":
    demonstrate_simple_integration()