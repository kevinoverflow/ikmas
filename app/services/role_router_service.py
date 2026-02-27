from __future__ import annotations

from typing import Dict, Optional

from app.domain.types import KnowledgeMode, RoleType, RoutingDecision, SECIPhase, UserModelSnapshot
from app.services.contracts import RoleRouterServiceContract


class RoleRouterService(RoleRouterServiceContract):
    _ROLE_MATRIX = {
        (KnowledgeMode.SWP, SECIPhase.SOCIALIZATION): "digital_memory_agent",
        (KnowledgeMode.SWP, SECIPhase.EXTERNALIZATION): "personal_context_restoration_agent",
        (KnowledgeMode.SWP, SECIPhase.COMBINATION): "adaptive_curator_agent",
        (KnowledgeMode.SWP, SECIPhase.INTERNALIZATION): "personal_context_restoration_agent",
        (KnowledgeMode.ESN, SECIPhase.SOCIALIZATION): "mentor_agent",
        (KnowledgeMode.ESN, SECIPhase.EXTERNALIZATION): "explanation_scribe_agent",
        (KnowledgeMode.ESN, SECIPhase.COMBINATION): "adaptive_curator_agent",
        (KnowledgeMode.ESN, SECIPhase.INTERNALIZATION): "tutor_agent",
        (KnowledgeMode.SKM, SECIPhase.SOCIALIZATION): "discovery_facilitator_agent",
        (KnowledgeMode.SKM, SECIPhase.EXTERNALIZATION): "hypothesis_formulation_agent",
        (KnowledgeMode.SKM, SECIPhase.COMBINATION): "concept_mining_agent",
        (KnowledgeMode.SKM, SECIPhase.INTERNALIZATION): "insight_transfer_agent",
    }

    _ROLE_TYPE_BY_ROLE_ID = {
        "digital_memory_agent": RoleType.CONTEXT_RESTORATION,
        "personal_context_restoration_agent": RoleType.CONTEXT_RESTORATION,
        "adaptive_curator_agent": RoleType.CURATOR,
        "mentor_agent": RoleType.MENTOR,
        "explanation_scribe_agent": RoleType.MENTOR,
        "tutor_agent": RoleType.TUTOR,
        "discovery_facilitator_agent": RoleType.CURATOR,
        "hypothesis_formulation_agent": RoleType.SIMULATION,
        "concept_mining_agent": RoleType.CURATOR,
        "insight_transfer_agent": RoleType.TUTOR,
    }

    def _normalize_mode(self, mode_override: Optional[str]) -> Optional[KnowledgeMode]:
        if not mode_override:
            return None
        raw = mode_override.upper()
        if raw in {"AUTO", ""}:
            return None
        if raw == KnowledgeMode.SWP.value:
            return KnowledgeMode.SWP
        if raw == KnowledgeMode.ESN.value:
            return KnowledgeMode.ESN
        if raw == KnowledgeMode.SKM.value:
            return KnowledgeMode.SKM
        return None

    def _infer_mode(self, message: str) -> tuple[KnowledgeMode, float, Dict[KnowledgeMode, float]]:
        text = (message or "").lower()
        score: Dict[KnowledgeMode, float] = {
            KnowledgeMode.SWP: 0.0,
            KnowledgeMode.ESN: 0.0,
            KnowledgeMode.SKM: 0.0,
        }
        for token in ("status", "entscheid", "todo", "to-do", "next action", "bring mich auf stand", "context"):
            if token in text:
                score[KnowledgeMode.SWP] += 1.0
        for token in ("was ist", "erklär", "explain", "define", "definition", "einsteiger", "glossar"):
            if token in text:
                score[KnowledgeMode.ESN] += 1.0
        for token in ("muster", "pattern", "outlier", "hypothese", "cross", "vergleich", "cluster"):
            if token in text:
                score[KnowledgeMode.SKM] += 1.0

        mode = max(score, key=score.get)
        values = sorted(score.values(), reverse=True)
        delta = values[0] - values[1]
        confidence = 0.55 + min(delta * 0.15, 0.35)
        return mode, max(0.0, min(confidence, 0.95)), score

    def _clarification_questions(self, mode: KnowledgeMode, score: Dict[KnowledgeMode, float]) -> list[str]:
        ranked = sorted(score.items(), key=lambda kv: kv[1], reverse=True)
        top = [m.value for m, _ in ranked[:2]]
        questions = [
            "Moechtest du eher: (1) Projektstatus/ToDos, (2) einfache Erklaerung, oder (3) Muster/Outliers?",
            f"Ich habe zwischen {', '.join(top)} die hoechste Naehe erkannt. Welcher Modus passt besser?",
        ]
        if mode == KnowledgeMode.SWP:
            questions.append("Soll ich dich auf Stand bringen (Decisions, offene Fragen, Actions, Risiken)?")
        elif mode == KnowledgeMode.ESN:
            questions.append("Soll ich wie fuer Einsteiger erklaeren mit Glossar und Beispiel?")
        else:
            questions.append("Soll ich auf cross-document Patterns, Outliers und Hypothesen fokussieren?")
        return questions

    def _policy_for(self, mode: KnowledgeMode) -> Dict[str, object]:
        if mode == KnowledgeMode.SWP:
            return {
                "k": 8,
                "mmr": False,
                "date_range_days": 90,
                "doctype": None,
                "rerank_strategy": "recent_first",
            }
        if mode == KnowledgeMode.ESN:
            return {
                "k": 5,
                "mmr": False,
                "date_range_days": None,
                "doctype": None,
                "rerank_strategy": "balanced",
            }
        return {
            "k": 10,
            "mmr": True,
            "date_range_days": None,
            "doctype": None,
            "rerank_strategy": "diverse_mmr",
        }

    def _schema_for(self, mode: KnowledgeMode) -> str:
        if mode == KnowledgeMode.SWP:
            return "swp_v1"
        if mode == KnowledgeMode.ESN:
            return "esn_v1"
        return "skm_v1"

    def route(
        self,
        message: str,
        mode_override: Optional[str],
        retrieval_signals: Dict[str, float],
        user_model: UserModelSnapshot,
        session_phase: SECIPhase,
    ) -> RoutingDecision:
        override_mode = self._normalize_mode(mode_override)
        if override_mode:
            mode = override_mode
            confidence = 0.98
            reason = "Using explicit mode override from user."
            suggestion = None
            clarification_questions = []
        else:
            mode, confidence, score = self._infer_mode(message)
            reason = "Inferred mode from user intent heuristics."
            suggestion = None
            clarification_questions = []
            if confidence < 0.7:
                suggestion = f"Low confidence auto routing. Consider switching mode manually ({mode.value})."
                clarification_questions = self._clarification_questions(mode, score)

        retrieval_confidence = float(retrieval_signals.get("retrieval_confidence", 0.0))
        if mode == KnowledgeMode.ESN and retrieval_confidence < 0.2 and user_model.knowledge_distance > 0.7:
            suggestion = "Sources are weak for novice explanation. Consider SWP for context first."
            if not clarification_questions:
                clarification_questions = [
                    "Soll ich zuerst einen SWP-Kontextueberblick geben und danach erklaeren?",
                ]

        role_id = self._ROLE_MATRIX[(mode, session_phase)]
        role_type = self._ROLE_TYPE_BY_ROLE_ID[role_id]
        return RoutingDecision(
            mode_distance=mode,
            seci_state=session_phase,
            role=role_type,
            role_id=role_id,
            output_schema_id=self._schema_for(mode),
            retrieval_policy=self._policy_for(mode),
            reason=reason,
            confidence=confidence,
            switch_suggestion=suggestion,
            clarification_questions=clarification_questions,
        )
