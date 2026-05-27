"""
Workflow Controller for executing structured agentic workflows.
"""
from typing import List, Dict, Any, Optional
from app.backend.workflow.task_models import (
    TaskPlan, 
    TaskSpec, 
    AgentTaskResult, 
    WorkflowResult, 
    ExecutionBudget, 
    AgentTrace, 
    AgentTraceNode
)
from app.backend.agents.registry import AGENT_REGISTRY
from app.backend.llm_client import LLMClient
from app.rag.llm import OpenAIChatBackend
from app.infrastructure.config import LLM_MODEL_NAME

class WorkflowController:
    """Central runtime component for agentic execution."""
    
    def __init__(self, budget: ExecutionBudget):
        self.budget = budget
    
    def validate_plan(self, plan: TaskPlan) -> bool:
        """Validate that the task plan is well-formed."""
        # Check if we have a valid aggregation strategy if tasks are present
        if plan.tasks and not plan.aggregation_strategy:
            raise ValueError("TaskPlan with tasks must specify an aggregation strategy")
        
        # Check that all tasks have valid agent roles
        for task in plan.tasks:
            if task.agent_role not in AGENT_REGISTRY:
                raise ValueError(f"Unknown agent role '{task.agent_role}' in task '{task.task_id}'")
        
        return True
    
    def enforce_budget(self, plan: TaskPlan) -> None:
        """Enforce execution budget limits."""
        # Check max subagents
        if len(plan.tasks) > self.budget.max_subagents:
            raise ValueError(f"Task plan exceeds max subagents limit ({self.budget.max_subagents})")
        
        # Check max depth - in this simplified version, we'll assume depth 1
        if self.budget.max_depth < 1:
            raise ValueError("Max depth must be at least 1")
    
    def resolve_dependencies(self, tasks: List[TaskSpec]) -> List[TaskSpec]:
        """Resolve task dependencies (simple implementation)."""
        # For now, we just return tasks in order (no complex dependency resolution)
        return tasks
    
    def execute_task(self, task: TaskSpec, context: Dict[str, Any]) -> AgentTaskResult:
        """Execute a single task using the registered agent."""
        # Get the agent class from registry
        if task.agent_role not in AGENT_REGISTRY:
            return AgentTaskResult(
                task_id=task.task_id,
                agent_role=task.agent_role,
                status="failed",
                error=f"Unknown agent role: {task.agent_role}"
            )
        
        # Create the agent instance and execute
        agent_class = AGENT_REGISTRY[task.agent_role]
        try:
            agent = agent_class()
            result = agent.execute(task, context)
            return result
        except Exception as e:
            return AgentTaskResult(
                task_id=task.task_id,
                agent_role=task.agent_role,
                status="failed",
                error=str(e)
            )
    
    def build_trace(self, results: List[AgentTaskResult], root_agent: str) -> AgentTrace:
        """Build execution trace from task results."""
        nodes = []
        total_tasks = len(results)
        successful_tasks = sum(1 for r in results if r.status == "success")
        failed_tasks = sum(1 for r in results if r.status == "failed")
        
        for result in results:
            node = AgentTraceNode(
                task_id=result.task_id,
                agent_role=result.agent_role,
                parent_agent=root_agent,
                status=result.status,
                error=result.error
            )
            nodes.append(node)
        
        return AgentTrace(
            root_agent=root_agent,
            nodes=nodes,
            total_tasks=total_tasks,
            successful_tasks=successful_tasks,
            failed_tasks=failed_tasks,
            max_depth_observed=1
        )
    
    def run(self, plan: TaskPlan, context: Dict[str, Any], root_agent: str = "unknown") -> WorkflowResult:
        """Execute the entire task plan."""
        # Validate the plan
        self.validate_plan(plan)
        
        # Enforce budget limits
        self.enforce_budget(plan)
        
        # Resolve dependencies
        ordered_tasks = self.resolve_dependencies(plan.tasks)
        
        # Execute tasks sequentially
        results = []
        for task in ordered_tasks:
            result = self.execute_task(task, context)
            results.append(result)
        
        # Build trace
        trace = self.build_trace(results, root_agent)
        
        # Return workflow result
        return WorkflowResult(
            results=results,
            trace=trace,
            aggregation_strategy=plan.aggregation_strategy,
            status="success" if trace.failed_tasks == 0 else "partial_success"
        )