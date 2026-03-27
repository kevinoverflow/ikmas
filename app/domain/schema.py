from __future__ import annotations
"""
Defines the strict JSON contract between the LLM, backend, and UI.

This module contains Pydantic models that enforce a deterministic and
fully structured response format for every assistant turn.
"""
from typing import Literal, Any
from pydantic import BaseModel, Field, ConfigDict
from app.domain.types import RoleName, TutorState

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