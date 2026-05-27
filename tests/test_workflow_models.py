import pytest
from app.backend.workflow.task_models import TaskPlan, TaskSpec, AgentTaskResult, WorkflowResult, ExecutionBudget, AgentTrace, AgentTraceNode
from app.backend.workflow.controller import WorkflowController
from app.backend.agents.registry import AGENT_REGISTRY
from app.backend.agents.workers.scribe_decision_extractor import ScribeDecisionExtractor
from app.backend.agents.workers.scribe_assumption_extractor import ScribeAssumptionExtractor
from app.backend.agents.workers.scribe_issue_extractor import ScribeIssueExtractor
from app.backend.aggregators.scribe_aggregator import ScribeAggregator

def test_task_plan_model():
    """Test TaskPlan model validation."""
    task_spec = TaskSpec(
        task_id="t1",
        task_type="extract_decisions",
        agent_role="scribe_decision_extractor",
        input_scope={"section": "Planning"},
        expected_output_schema="DecisionExtractionResult"
    )
    
    plan = TaskPlan(
        should_decompose=True,
        rationale="Test rationale",
        tasks=[task_spec],
        aggregation_strategy="scribe_knowledge_artifact"
    )
    
    assert plan.should_decompose == True
    assert plan.rationale == "Test rationale"
    assert len(plan.tasks) == 1
    assert plan.aggregation_strategy == "scribe_knowledge_artifact"

def test_task_spec_model():
    """Test TaskSpec model."""
    task_spec = TaskSpec(
        task_id="t1",
        task_type="extract_decisions",
        agent_role="scribe_decision_extractor",
        input_scope={"section": "Planning"},
        expected_output_schema="DecisionExtractionResult",
        dependencies=["t2"],
        priority=1
    )
    
    assert task_spec.task_id == "t1"
    assert task_spec.task_type == "extract_decisions"
    assert task_spec.agent_role == "scribe_decision_extractor"
    assert task_spec.input_scope == {"section": "Planning"}
    assert task_spec.expected_output_schema == "DecisionExtractionResult"
    assert task_spec.dependencies == ["t2"]
    assert task_spec.priority == 1

def test_agent_task_result_model():
    """Test AgentTaskResult model."""
    result = AgentTaskResult(
        task_id="t1",
        agent_role="scribe_decision_extractor",
        status="success",
        output={"decisions": []},
        citations=[],
        artefacts=[],
        telemetry={}
    )
    
    assert result.task_id == "t1"
    assert result.agent_role == "scribe_decision_extractor"
    assert result.status == "success"
    assert result.output == {"decisions": []}

def test_execution_budget_model():
    """Test ExecutionBudget model."""
    budget = ExecutionBudget(
        max_subagents=3,
        max_depth=1,
        max_total_tokens=10000,
        max_wall_time_seconds=30,
        max_retrieval_calls=5,
        allow_parallel_execution=True
    )
    
    assert budget.max_subagents == 3
    assert budget.max_depth == 1
    assert budget.allow_parallel_execution == True

def test_workflow_controller_initialization():
    """Test WorkflowController initialization."""
    budget = ExecutionBudget()
    controller = WorkflowController(budget)
    
    assert controller.budget == budget

def test_agent_registry():
    """Test that all expected agents are registered."""
    assert "scribe_decision_extractor" in AGENT_REGISTRY
    assert "scribe_assumption_extractor" in AGENT_REGISTRY
    assert "scribe_issue_extractor" in AGENT_REGISTRY
    
    # Test that registered agents are instantiable
    assert AGENT_REGISTRY["scribe_decision_extractor"] == ScribeDecisionExtractor
    assert AGENT_REGISTRY["scribe_assumption_extractor"] == ScribeAssumptionExtractor
    assert AGENT_REGISTRY["scribe_issue_extractor"] == ScribeIssueExtractor

def test_scribe_aggregator():
    """Test ScribeAggregator basic functionality."""
    aggregator = ScribeAggregator()
    
    # Create some mock results
    result1 = AgentTaskResult(
        task_id="t1",
        agent_role="scribe_decision_extractor",
        status="success",
        output={
            "decisions": [{"decision": "Test decision", "rationale": "Test rationale"}],
            "section": "Planning"
        }
    )
    
    result2 = AgentTaskResult(
        task_id="t2",
        agent_role="scribe_issue_extractor",
        status="success",
        output={
            "open_issues": [{"issue": "Test issue", "description": "Test description"}],
            "section": "Risks"
        }
    )
    
    results = [result1, result2]
    artifact = aggregator.aggregate(results)
    
    assert artifact.artifact_type == "reusable_knowledge_artifact"
    assert len(artifact.decisions) == 1
    assert len(artifact.open_issues) == 1
    assert len(artifact.source_map) == 2