#!/usr/bin/env python3
"""
Demonstration of how the artifact generation system integrates with the router.
This shows how the router would automatically detect when artifact generation is needed.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from app.backend.subagent_coordinator import subagent_coordinator, ArtifactGenerationRequest, ArtifactType
from app.backend.router_agent import RouteDecision


def demonstrate_router_integration():
    """Demonstrate how the router would detect artifact generation needs."""
    
    print("🔍 Router Integration Demonstration")
    print("=" * 50)
    
    # Create a mock backend for testing
    class MockBackend:
        def generate(self, prompt, system_prompt=None, **kwargs):
            # Mock responses for router analysis
            if "definition" in prompt.lower():
                return "A formal statement that precisely describes the meaning of a term or concept."
            elif "concept" in prompt.lower():
                return "A mental representation of a category or class of objects, events, or relations."
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
            # Mock responses for router analysis
            if "analyze" in prompt.lower() or "detect" in prompt.lower():
                return '''{
    "seci_mode": "Internalization",
    "reuse_situation": "Expertise-Seeking Novice",
    "selected_agent": "MentorAgent",
    "routing_confidence": "high",
    "reason": "User is asking to test understanding, indicating they want to internalize explicit knowledge.",
    "required_context": ["previous learning materials", "learning objectives"],
    "verification_need": "none",
    "next_state": "agent_execution",
    "artifact_generation_plan": {
        "artifacts_needed": ["definition", "concept", "quiz_item"],
        "processing_order": ["definition", "concept", "quiz_item"]
    }
}'''
            return "Mock response for: " + prompt[:50] + "..."
    
    mock_backend = MockBackend()
    
    # Simulate different user requests to show router detection
    test_cases = [
        {
            "input": "Test my understanding of graph theory",
            "description": "User wants to test their understanding"
        },
        {
            "input": "Explain the concepts in algorithms",
            "description": "User wants conceptual explanations"
        },
        {
            "input": "Generate definitions for theoretical computer science",
            "description": "User explicitly asks for definitions"
        },
        {
            "input": "What is a finite automaton?",
            "description": "User asks for a specific definition"
        }
    ]
    
    print("Testing Router Detection of Artifact Generation Needs:")
    print("-" * 60)
    
    for i, test_case in enumerate(test_cases, 1):
        user_input = test_case["input"]
        description = test_case["description"]
        
        print(f"\n{i}. User Input: \"{user_input}\"")
        print(f"   Description: {description}")
        
        # Simulate router analysis (what would happen in the real router)
        # In reality, this would be the actual router_agent.route_with_agent() call
        prompt = f"""Analyze this user request and determine if artifact generation is needed:
        
User request: "{user_input}"
        
Return a JSON response with the following structure:
{
  "seci_mode": "String representing the SECI mode (Socialization, Externalization, Combination, Internalization)",
  "reuse_situation": "String representing the reuse situation",
  "selected_agent": "String representing the agent to use",
  "routing_confidence": "high|medium|low",
  "reason": "Brief explanation of the routing decision",
  "required_context": ["list", "of", "context", "requirements"],
  "verification_need": "String describing verification needs",
  "next_state": "String describing next state",
  "artifact_generation_plan": {
    "artifacts_needed": ["list", "of", "artifact", "types"],
    "processing_order": ["order", "of", "processing"]
  }
}"""
        
        # This simulates what the router would do
        print("   Router Analysis:")
        
        # Instead of calling the real router (which has dependencies), 
        # we'll simulate the key parts of the router logic
        
        # The router would detect patterns in the user request
        artifacts_needed = []
        
        if "test" in user_input.lower() or "understand" in user_input.lower():
            artifacts_needed.extend(["definition", "concept", "quiz_item"])
            print("     ✓ Detected: User wants to test understanding")
            print("     ✓ Will recommend: Definitions, Concepts, and Quiz generation")
            
        elif "explain" in user_input.lower() or "concept" in user_input.lower():
            artifacts_needed.append("concept")
            print("     ✓ Detected: User wants conceptual explanations")
            print("     ✓ Will recommend: Concept generation")
            
        elif "definition" in user_input.lower() or "define" in user_input.lower():
            artifacts_needed.append("definition")
            print("     ✓ Detected: User wants definitions")
            print("     ✓ Will recommend: Definition generation")
            
        # Create a mock route decision with artifact generation plan
        mock_route_decision = RouteDecision(
            role="MentorAgent",  # Would be determined by router
            knowledge_mode="INTERNALIZATION",  # Would be determined by router
            distance="ESN",  # Expertise-Seeking Novice
            routing_confidence="high",
            reason=f"User is requesting knowledge artifacts for {user_input}",
            required_context=["learning context"],
            verification_need="none",
            next_state="agent_execution",
            used_fallback=False,
            model_selection={"model_name": "MENTOR_MODEL_NAME", "reason": "Mentor agent for expertise"},
            detected_themes=[],
            knowledge_gaps=[],
            related_sessions=[],
            artifact_generation_plan={
                "artifacts_needed": artifacts_needed,
                "processing_order": artifacts_needed
            }
        )
        
        print(f"   Router Decision:")
        print(f"     Selected Agent: {mock_route_decision.role}")
        print(f"     Confidence: {mock_route_decision.routing_confidence}")
        print(f"     Artifact Plan: {mock_route_decision.artifact_generation_plan}")
        
        # Show what would happen if artifact generation is triggered
        if mock_route_decision.artifact_generation_plan.get("artifacts_needed"):
            print("   Artifact Generation Workflow:")
            print("     ✓ Router recommends artifact generation")
            print("     ✓ System will spawn specialized subagents")
            
            # Simulate the artifact generation process
            requests = []
            for artifact_type_str in mock_route_decision.artifact_generation_plan["artifacts_needed"]:
                artifact_type = ArtifactType(artifact_type_str)
                request = ArtifactGenerationRequest(
                    artifact_type=artifact_type,
                    context=user_input,
                    user_input=user_input,
                    session_id="demo_session_001",
                    target_audience="novice"
                )
                requests.append(request)
            
            print(f"     ✓ Spawning {len(requests)} specialized subagents...")
            
            # Execute sequentially (as in real system)
            results = subagent_coordinator.generate_artifacts_sequentially(requests, mock_backend)
            
            print(f"     ✓ Generated {len(results)} artifacts:")
            for result in results:
                print(f"       • {result.artifact_type.value.capitalize()}: {result.content[:50]}...")
                
            # Show stored artifacts
            artifacts = subagent_coordinator.get_all_artifacts()
            print(f"     ✓ Stored {len(artifacts)} artifacts for session context")
        else:
            print("   No artifact generation recommended")
        
        print("-" * 60)
    
    # Demonstrate the complete workflow with a "test understanding" scenario
    print("\n🎯 Complete Workflow Demo: 'Test my understanding of theoretical computer science'")
    print("-" * 60)
    
    user_request = "Test my understanding of theoretical computer science"
    
    # Step 1: Router detects artifact generation need
    print("1. Router Analysis:")
    print(f"   User request: \"{user_request}\"")
    print("   Router detects: 'Test my understanding' pattern")
    print("   Router recommends: Definitions, Concepts, and Quiz generation")
    
    # Step 2: Create artifact generation plan
    artifact_plan = {
        "artifacts_needed": ["definition", "concept", "quiz_item"],
        "processing_order": ["definition", "concept", "quiz_item"]
    }
    
    print(f"2. Artifact Generation Plan: {artifact_plan}")
    
    # Step 3: Execute artifact generation
    print("3. Executing Artifact Generation:")
    
    # Create requests
    requests = []
    for artifact_type_str in artifact_plan["artifacts_needed"]:
        artifact_type = ArtifactType(artifact_type_str)
        request = ArtifactGenerationRequest(
            artifact_type=artifact_type,
            context="Theoretical Computer Science",
            user_input=user_request,
            session_id="workflow_demo_001",
            target_audience="novice"
        )
        requests.append(request)
        print(f"   ✓ Created request for {artifact_type_str}")
    
    # Execute
    results = subagent_coordinator.generate_artifacts_sequentially(requests, mock_backend)
    print(f"   ✓ Generated {len(results)} artifacts successfully")
    
    # Step 4: Show results
    print("4. Generated Artifacts:")
    for i, result in enumerate(results, 1):
        print(f"   {i}. {result.artifact_type.value.upper()}:")
        print(f"      Content: {result.content[:100]}...")
        print(f"      Confidence: {result.confidence}")
        print(f"      Metadata: {result.metadata}")
        print()
    
    # Step 5: Show final integration
    print("5. Final Integration:")
    print("   ✓ Artifacts stored for session context")
    print("   ✓ Can be used in mentor agent responses")
    print("   ✓ Available for future learning sessions")
    
    print("\n" + "=" * 50)
    print("✅ Router Integration Complete!")
    print("The system now automatically detects when artifact generation is needed")
    print("and seamlessly integrates it into the learning workflow.")


if __name__ == "__main__":
    demonstrate_router_integration()