from __future__ import annotations
"""
Defines the strict JSON contract between the LLM, backend, and UI.

This module contains Pydantic models that enforce a deterministic and
fully structured response format for every assistant turn.
"""
from typing import Literal, Any
from pydantic import BaseModel, Field, ConfigDict
from app.domain.types import RoleName, TutorState
from app.backend.workflow.task_models import TaskPlan, AgentTrace

class Question(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    type: Literal["single_choice", "multi_choice", "text"]
    label: str
    options: list[str] = Field(default_factory=list)
    required: bool=True

class Artefact(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["summary", "flashcards", "quiz", "checklist", "note", "concept_map"]
    title: str
    content: str
    concept_ids: list[int] = Field(default_factory=list)

class Action(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["ask", "store_artefact", "schedule_review", "update_mastery", "none"]
    payload: dict[str, Any] = Field(default_factory=dict)

class Citation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source: str
    chunk_id: str
    title: str | None = None
    locator: str | None = None

class Telemetry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    intent: str
    distance: str
    confidence: float
    retrieval_count: int
    repair_used: bool
    fallback_used: bool


class RouterDebug(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: RoleName
    knowledge_mode: str
    distance: str
    model_name: str
    model_reason: str
    routing_confidence: str
    reason: str
    required_context: list[str] = Field(default_factory=list)
    verification_need: str
    next_state: str
    used_fallback: bool


class AssistantPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: RoleName
    state: TutorState | None = None
    assistant_message: str
    questions: list[Question]
    artefacts: list[Artefact]
    actions: list[Action]
    citations: list[Citation]
    telemetry: Telemetry
    router_debug: RouterDebug | None = None
    task_plan: TaskPlan | None = None
    agent_trace: AgentTrace | None = None
    workflow_result: dict | None = None


class RouterPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    seci_mode: Literal["Socialization", "Externalization", "Combination", "Internalization"]
    reuse_situation: Literal[
        "Shared Work Producer",
        "Shared Work Practitioner",
        "Expertise-Seeking Novice",
        "Secondary Knowledge Miner",
    ]
    selected_agent: RoleName
    routing_confidence: Literal["low", "medium", "high"]
    reason: str
    required_context: list[str] = Field(default_factory=list)
    verification_need: str
    next_state: str
