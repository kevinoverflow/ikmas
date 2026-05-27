#!/usr/bin/env python3
"""
Integration test to demonstrate the workflow system functionality.
"""

def test_workflow_components():
    """Test that all workflow components can be imported and instantiated."""
    
    # Test imports
    from app.backend.workflow.task_models import (
        TaskPlan, TaskSpec, AgentTaskResult, WorkflowResult, 
        ExecutionBudget, AgentTrace, AgentTraceNode
    )
    
    from app.backend.workflow.controller import WorkflowController
    from app.backend.agents.registry import AGENT_REGISTRY
    from app.backend.aggregators.scribe_aggregator import ScribeAggregator
    from app.backend.agents.workers.scribe_decision_extractor import ScribeDecisionExtractor
    from app.backend.agents.workers.scribe_assumption_extractor import ScribeAssumptionExtractor
    from app.backend.agents.workers.scribe_issue_extractor import ScribeIssueExtractor
    
    print("✓ All imports successful")
    
    # Test TaskSpec creation
    task_spec = TaskSpec(
        task_id="test_task_1",
        task_type="extract_decisions",
        agent_role="scribe_decision_extractor",
        input_scope={"section": "Meeting Notes"},
        expected_output_schema="DecisionExtractionResult"
    )
    
    print("✓ TaskSpec creation successful")
    
    # Test TaskPlan creation
    task_plan = TaskPlan(
        should_decompose=True,
        rationale="Complex input with multiple sections requiring decomposition",
        tasks=[task_spec],
        aggregation_strategy="scribe_knowledge_artifact"
    )
    
    print("✓ TaskPlan creation successful")
    
    # Test registry
    assert "scribe_decision_extractor" in AGENT_REGISTRY
    assert "scribe_assumption_extractor" in AGENT_REGISTRY
    assert "scribe_issue_extractor" in AGENT_REGISTRY
    
    print("✓ Agent registry functional")
    
    # Test that agent classes can be instantiated
    decision_extractor = ScribeDecisionExtractor()
    assumption_extractor = ScribeAssumptionExtractor()
    issue_extractor = ScribeIssueExtractor()
    
    print("✓ Agent classes instantiable")
    
    # Test workflow controller
    budget = ExecutionBudget()
    controller = WorkflowController(budget)
    
    print("✓ WorkflowController instantiation successful")
    
    # Test aggregator
    aggregator = ScribeAggregator()
    print("✓ ScribeAggregator instantiation successful")
    
    print("\nAll workflow components are properly integrated!")
    return True

if __name__ == "__main__":
    test_workflow_components()