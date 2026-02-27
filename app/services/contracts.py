from __future__ import annotations

from typing import Dict, List, Optional, Protocol, Tuple

from app.domain.types import (
    InternalizationState,
    RetrievalResult,
    RoutingDecision,
    SECIPhase,
    UserModelSnapshot,
)


class KnowledgeServiceContract(Protocol):
    def upload_files(
        self, collection_id: str, files: List[Tuple[str, bytes]], on_name_conflict: str = "skip"
    ) -> Dict[str, int]:
        ...

    def rebuild_index(self, collection_id: str, reindex: bool = False) -> int:
        ...

    def query(
        self,
        collection_id: str,
        question: str,
        chat_history: Optional[List[Dict[str, str]]] = None,
        k_retrieve: int = 30,
        k_final: int = 5,
    ) -> RetrievalResult:
        ...


class UserModelServiceContract(Protocol):
    def get_snapshot(self, user_id: str) -> UserModelSnapshot:
        ...

    def update_assessment(self, user_id: str, topic: str, score: float, confidence: float) -> None:
        ...

    def schedule_review(self, user_id: str, due_at: str, reason: str) -> None:
        ...

    def get_schedule(self, user_id: str) -> List[Dict[str, str]]:
        ...


class RoleRouterServiceContract(Protocol):
    def route(
        self,
        message: str,
        mode_override: Optional[str],
        retrieval_signals: Dict[str, float],
        user_model: UserModelSnapshot,
        session_phase: SECIPhase,
    ) -> RoutingDecision:
        ...


class SECIWorkflowServiceContract(Protocol):
    def start_session(self, user_id: str, phase: SECIPhase = SECIPhase.SOCIALIZATION) -> Dict[str, str]:
        ...

    def get_session(self, session_id: str) -> Dict[str, object]:
        ...

    def apply_event(
        self,
        session_id: str,
        event_type: str,
        target_phase: Optional[SECIPhase] = None,
        target_state: Optional[InternalizationState] = None,
        reason: str = "",
    ) -> Dict[str, object]:
        ...


class TutoringServiceContract(Protocol):
    def run_assessment(self, user_id: str, topic: str, score: float, confidence: float) -> Dict[str, object]:
        ...

    def run_practice(self, user_id: str, prompt: str, quality_score: float) -> Dict[str, object]:
        ...
