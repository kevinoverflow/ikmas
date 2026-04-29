from __future__ import annotations
"""
Shared domain types for the orchestration layer.

This module defines the core enums and dataclasses used across the backend:
- intent classification
- knowledge distance estimation
- role routing
- retrieval results
- persistent turn logging

These types act as a lightweight contract between orchestrator, retrieval,
FSM, storage, and UI layers.
"""
from dataclasses import dataclass, field
from typing import Any, Literal, TypedDict

Intent = Literal[
    "what_is",
    "simplify",
    "project_specific",
    "cross_context",
    "pattern_mining",
    "learn_mode",
]

Distance = Literal["ESN", "SWP", "SWPr", "SKM"]

KnowledgeMode = Literal[
    "SOCIALIZATION",
    "EXTERNALIZATION",
    "COMBINATION",
    "INTERNALIZATION",
]

RoleName = Literal[
    "ScribeAgent",
    "SemanticLinkingAgent",
    "MentorAgent",
    "ContextReconstructorAgent",
]

ALL_ROLE_NAMES: tuple[str, ...] = (
    "ScribeAgent",
    "SemanticLinkingAgent",
    "MentorAgent",
    "ContextReconstructorAgent",
)

TutorState = Literal[
    "ASSESS",
    "EXPLAIN",
    "CHECK",
    "PRACTICE",
    "FEEDBACK",
    "SCHEDULE",
]

QuestionType=Literal["single_choice","multi_choice","text"]

@dataclass
class RetrievedChunk:
    chunk_id: str
    text: str
    source: str
    title: str | None = None
    page : int | None = None
    score: float = 0.0
    meta: dict[str, Any] = field(default_factory=dict)

@dataclass
class RetrievalResult:
    chunks: list[RetrievedChunk]
    top1: float 
    avg_top3: float
    coverage: float
    confidence: float

@dataclass(frozen=True)
class ImageTextResult:
    text: str
    chunk_type: Literal["ocr_text", "image_description"]
    processor: Literal["ocr", "vision"]
    confidence: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass
class TurnRecord:
    session_id:str
    user_input: str
    intent: str
    distance: str
    role: str
    confidence: float
    llm_json: str
    system_state: str
    user_id:str | None = None
    state: str | None = None

class ChatTurn(TypedDict):
    user: str
    bot: str
    sources: list[Any]  # später: besser typisieren (Document)
