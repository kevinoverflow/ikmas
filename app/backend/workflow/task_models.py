from __future__ import annotations
from typing import Literal, List, Dict, Any, Optional
from pydantic import BaseModel, Field
from app.domain.types import RoleName

# Task models for agentic workflow architecture

class TaskSpec(BaseModel):
    """Describes a single bounded unit of work."""
    task_id: str
    task_type: str
    agent_role: str
    input_scope: Dict[str, Any]
    expected_output_schema: str
    dependencies: List[str] = Field(default_factory=list)
    priority: int = 0
    max_tokens: Optional[int] = None
    timeout_seconds: Optional[int] = None

class TaskPlan(BaseModel):
    """Structured output of a parent agent when decomposition is useful."""
    should_decompose: bool
    rationale: str
    tasks: List[TaskSpec] = Field(default_factory=list)
    aggregation_strategy: Optional[str] = None

class AgentTaskResult(BaseModel):
    """Result from executing a single task."""
    task_id: str
    agent_role: str
    status: Literal["success", "failed", "skipped"]
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    citations: List[Dict[str, Any]] = Field(default_factory=list)
    artefacts: List[Dict[str, Any]] = Field(default_factory=list)
    telemetry: Dict[str, Any] = Field(default_factory=dict)

class AgentTraceNode(BaseModel):
    """A node in the agent execution trace."""
    task_id: str
    agent_role: str
    parent_agent: Optional[str] = None
    status: Literal["planned", "running", "success", "failed", "skipped"]
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    dependencies: List[str] = Field(default_factory=list)
    error: Optional[str] = None

class AgentTrace(BaseModel):
    """Complete trace of agent execution."""
    root_agent: str
    nodes: List[AgentTraceNode] = Field(default_factory=list)
    total_tasks: int = 0
    successful_tasks: int = 0
    failed_tasks: int = 0
    max_depth_observed: int = 0

class ExecutionBudget(BaseModel):
    """Defines limits for agentic workflows."""
    max_subagents: int = 5
    max_depth: int = 2
    max_total_tokens: int = 12000
    max_wall_time_seconds: int = 60
    max_retrieval_calls: int = 8
    allow_parallel_execution: bool = False

class WorkflowResult(BaseModel):
    """Final result of a workflow execution."""
    results: List[AgentTaskResult]
    trace: AgentTrace
    aggregation_strategy: Optional[str] = None
    status: Literal["success", "partial_success", "failed"] = "success"
    message: Optional[str] = None