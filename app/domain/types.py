from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


class SECIPhase(str, Enum):
    SOCIALIZATION = "socialization"
    EXTERNALIZATION = "externalization"
    COMBINATION = "combination"
    INTERNALIZATION = "internalization"


class InternalizationState(str, Enum):
    ASSESS = "assess"
    EXPLAIN = "explain"
    CHECK = "check"
    PRACTICE = "practice"
    FEEDBACK = "feedback"
    SCHEDULE = "schedule"


class RoleType(str, Enum):
    TUTOR = "tutor"
    MENTOR = "mentor"
    SIMULATION = "simulation"
    CURATOR = "curator"
    CONTEXT_RESTORATION = "context_restoration"


class LearningArtifactType(str, Enum):
    DECISION_RECORD = "decision_record"
    CASE_CARD = "case_card"
    FAQ = "faq"
    SOP_DRAFT = "sop_draft"


class KnowledgeMode(str, Enum):
    SWP = "SWP"
    SWPr = "SWPr"
    ESN = "ESN"
    SKM = "SKM"


@dataclass
class RetrievalResult:
    answer: str
    sources: List[Dict[str, Any]]
    confidence: float
    retrieved_count: int


@dataclass
class UserModelSnapshot:
    user_id: str
    knowledge_distance: float = 0.5
    learning_progress: float = 0.0
    goal: Optional[str] = None
    next_review_at: Optional[str] = None


@dataclass
class RoutingDecision:
    mode_distance: KnowledgeMode
    seci_state: SECIPhase
    role: RoleType
    role_id: str
    output_schema_id: str
    retrieval_policy: Dict[str, Any]
    reason: str
    confidence: float
    switch_suggestion: Optional[str] = None
    clarification_questions: Optional[List[str]] = None


@dataclass
class ChatFilters:
    date_range_days: Optional[int] = None
    doctype: Optional[List[str]] = None
    k: int = 5
    mmr: bool = False


@dataclass
class Citation:
    sid: str
    source: str
    page: Optional[int]
    chunk_id: str
    snippet: str
    metadata: Dict[str, Any]


@dataclass
class ModeValidationResult:
    schema_ok: bool
    errors: List[str]
