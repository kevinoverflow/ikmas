from __future__ import annotations

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from app.domain.types import InternalizationState, KnowledgeMode, SECIPhase


class IndexRebuildRequest(BaseModel):
    collection_id: str = "default"
    project_id: Optional[str] = None
    reindex: bool = False


class QueryRequest(BaseModel):
    collection_id: str = "default"
    question: str
    chat_history: List[Dict[str, str]] = Field(default_factory=list)
    user_id: str = "anonymous"
    session_phase: SECIPhase = SECIPhase.INTERNALIZATION
    k_retrieve: int = 30
    k_final: int = 5


class QueryResponse(BaseModel):
    answer: str
    sources: List[Dict[str, object]]
    retrieval_confidence: float
    retrieved_count: int
    role: str
    routing_reason: str
    routing_confidence: float


class StartSessionRequest(BaseModel):
    user_id: str
    phase: SECIPhase = SECIPhase.SOCIALIZATION


class SessionEventRequest(BaseModel):
    event_type: str
    target_phase: Optional[SECIPhase] = None
    target_state: Optional[InternalizationState] = None
    reason: str = ""


class AssessmentRequest(BaseModel):
    topic: str = "global"
    score: float = Field(..., ge=0.0, le=1.0)
    confidence: float = Field(0.6, ge=0.0, le=1.0)


class PracticeRequest(BaseModel):
    prompt: str
    quality_score: float = Field(..., ge=0.0, le=1.0)


class ProjectCreateRequest(BaseModel):
    name: str


class ProjectResponse(BaseModel):
    id: str
    name: str
    collection_id: str
    created_at: Optional[str] = None


class ChatFiltersRequest(BaseModel):
    date_range_days: Optional[int] = Field(default=None, ge=1, le=3650)
    doctype: Optional[List[str]] = None
    k: int = Field(default=5, ge=1, le=20)
    mmr: bool = False


class RouterPreviewRequest(BaseModel):
    message: str
    mode_override: Optional[Literal["AUTO", "SWP", "ESN", "SKM"]] = "AUTO"
    user_id: str = "anonymous"
    project_id: Optional[str] = None
    session_id: Optional[str] = None
    retrieval_confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class RetrievalPolicyResponse(BaseModel):
    k: int
    mmr: bool
    date_range_days: Optional[int] = None
    doctype: Optional[List[str]] = None
    rerank_strategy: str


class RouterInfoResponse(BaseModel):
    mode_distance: Literal["SWP", "ESN", "SKM"]
    seci_state: SECIPhase
    role_id: str
    confidence: float
    output_schema_id: Literal["swp_v1", "esn_v1", "skm_v1"]
    retrieval_policy: RetrievalPolicyResponse
    switch_suggestion: Optional[str] = None
    clarification_questions: List[str] = Field(default_factory=list)
    reason: str


class SWPDecision(BaseModel):
    what: str
    why: str
    source_ids: List[str]


class SWPOpenQuestion(BaseModel):
    question: str
    source_ids: List[str]


class SWPAction(BaseModel):
    action: str
    owner: str = ""
    due: str = ""
    source_ids: List[str]


class SWPRisk(BaseModel):
    risk: str
    mitigation: str
    source_ids: List[str]


class SWPOutput(BaseModel):
    tldr: str
    decisions: List[SWPDecision]
    open_questions: List[SWPOpenQuestion]
    next_actions: List[SWPAction]
    risks: List[SWPRisk]


class GlossaryItem(BaseModel):
    term: str
    meaning: str


class SourceExample(BaseModel):
    example: str
    source_ids: List[str]


class ESNOutput(BaseModel):
    simple_explanation: str
    glossary: List[GlossaryItem]
    example_from_sources: SourceExample
    common_pitfalls: List[str]


class SWPrCase(BaseModel):
    case_summary: str
    source_ids: List[str]


class SWPrGuideline(BaseModel):
    guideline: str
    local_adaptation: str
    source_ids: List[str]


class SWPrOutput(BaseModel):
    practitioner_brief: str
    transferable_cases: List[SWPrCase]
    actionable_guidelines: List[SWPrGuideline]
    simulation_prompt: str


class PatternItem(BaseModel):
    pattern: str
    evidence: List[str]


class OutlierItem(BaseModel):
    outlier: str
    evidence: List[str]


class HypothesisItem(BaseModel):
    hypothesis: str
    confidence: Literal["low", "medium", "high"] = "medium"
    evidence: List[str]


class SKMOutput(BaseModel):
    patterns: List[PatternItem]
    outliers: List[OutlierItem]
    hypotheses: List[HypothesisItem]


class CitationResponse(BaseModel):
    sid: str
    source: str
    page: Optional[int]
    chunk_id: str
    snippet: str
    metadata: Dict[str, object]


class ChatRequest(BaseModel):
    project_id: str
    mode: Optional[KnowledgeMode] = None
    mode_override: Optional[Literal["AUTO", "SWP", "ESN", "SKM"]] = None
    message: str
    filters: ChatFiltersRequest = Field(default_factory=ChatFiltersRequest)
    strict_sources_only: bool = False
    strict_citations: Optional[bool] = None
    user_id: str = "anonymous"
    session_id: Optional[str] = None


class ValidationInfo(BaseModel):
    schema_ok: bool
    errors: List[str]
    citation_coverage: float = 0.0
    completeness_score: float = 0.0
    insufficient_evidence: bool = False
    missing_fields: List[str] = Field(default_factory=list)


class ChatResponse(BaseModel):
    mode: Literal["SWP", "ESN", "SKM"]
    data: Dict[str, object]
    narrative_answer: str = ""
    citations: List[CitationResponse]
    why_sources: List[str]
    retrieval: Dict[str, object]
    router: RouterInfoResponse
    validation: ValidationInfo
    role: str
    routing_reason: str
    routing_confidence: float


class OnboardingRequest(BaseModel):
    project_id: str
    mode: KnowledgeMode = KnowledgeMode.SWP
    filters: ChatFiltersRequest = Field(default_factory=ChatFiltersRequest)
    strict_sources_only: bool = True
    strict_citations: Optional[bool] = None
    user_id: str = "anonymous"
    session_id: Optional[str] = None
