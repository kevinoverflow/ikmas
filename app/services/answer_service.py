from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple, Type

from pydantic import BaseModel, ValidationError

from app.api.schemas import ESNOutput, SKMOutput, SWPOutput
from app.domain.types import ChatFilters, Citation, KnowledgeMode, ModeValidationResult
from app.infrastructure.config import LANGUAGE_MODEL_NAME
from app.rag.llm import get_client


SCHEMA_MODEL_MAP: Dict[KnowledgeMode, Type[BaseModel]] = {
    KnowledgeMode.SWP: SWPOutput,
    KnowledgeMode.ESN: ESNOutput,
    KnowledgeMode.SKM: SKMOutput,
}

PROMPT_BY_MODE: Dict[KnowledgeMode, str] = {
    KnowledgeMode.SWP: "Return ONLY valid JSON following this schema: "
    '{"tldr":"","decisions":[{"what":"","why":"","source_ids":["S1"]}],"open_questions":[{"question":"","source_ids":["S1"]}],"next_actions":[{"action":"","owner":"","due":"","source_ids":["S1"]}],"risks":[{"risk":"","mitigation":"","source_ids":["S1"]}]}.',
    KnowledgeMode.ESN: "Return ONLY valid JSON following this schema: "
    '{"simple_explanation":"","glossary":[{"term":"","meaning":""}],"example_from_sources":{"example":"","source_ids":["S1"]},"common_pitfalls":[]}.',
    KnowledgeMode.SKM: "Return ONLY valid JSON following this schema: "
    '{"patterns":[{"pattern":"","evidence":["S1"]}],"outliers":[{"outlier":"","evidence":["S1"]}],"hypotheses":[{"hypothesis":"","confidence":"low|medium|high","evidence":["S1"]}]}.',
}


class AnswerService:
    _SCHEMA_TO_MODE = {
        "swp_v1": KnowledgeMode.SWP,
        "esn_v1": KnowledgeMode.ESN,
        "skm_v1": KnowledgeMode.SKM,
    }

    def _build_context(self, citations: List[Citation]) -> str:
        chunks = []
        for c in citations:
            chunks.append(f"[{c.sid}] source={c.source} page={c.page}\n{c.snippet}")
        return "\n\n".join(chunks)

    def _try_parse_json(self, text: str) -> Dict[str, Any]:
        text = text.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:].strip()
        return json.loads(text)

    def _validate_mode_payload(self, mode: KnowledgeMode, payload: Dict[str, Any]) -> Tuple[Dict[str, Any], ModeValidationResult]:
        model_cls = SCHEMA_MODEL_MAP[mode]
        try:
            parsed = model_cls.model_validate(payload)
            return parsed.model_dump(), ModeValidationResult(schema_ok=True, errors=[])
        except ValidationError as exc:
            return {}, ModeValidationResult(schema_ok=False, errors=[str(exc)])

    def _collect_evidence_fields(self, node: Any) -> tuple[int, int, List[str]]:
        total = 0
        covered = 0
        invalid: List[str] = []

        def _walk(obj: Any) -> None:
            nonlocal total, covered
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key in {"source_ids", "evidence"} and isinstance(value, list):
                        total += 1
                        if value:
                            covered += 1
                        for sid in value:
                            if not isinstance(sid, str) or not sid.startswith("S"):
                                invalid.append(str(sid))
                    _walk(value)
            elif isinstance(obj, list):
                for item in obj:
                    _walk(item)

        _walk(node)
        return total, covered, invalid

    def _enforce_allowed_source_ids(self, payload: Dict[str, Any], allowed: set[str]) -> List[str]:
        errors: List[str] = []

        def _walk(obj: Any, path: str) -> None:
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key in {"source_ids", "evidence"} and isinstance(value, list):
                        for idx, sid in enumerate(value):
                            if sid not in allowed:
                                errors.append(f"{path}.{key}[{idx}] contains invalid source id '{sid}'")
                    _walk(value, f"{path}.{key}")
            elif isinstance(obj, list):
                for idx, item in enumerate(obj):
                    _walk(item, f"{path}[{idx}]")

        _walk(payload, "$")
        return errors

    def assess_completeness(self, output_schema_id: str, payload: Dict[str, Any]) -> tuple[float, List[str], bool]:
        missing: List[str] = []

        def _is_empty(value: Any) -> bool:
            if value is None:
                return True
            if isinstance(value, str):
                return value.strip() == ""
            if isinstance(value, list):
                return len(value) == 0
            if isinstance(value, dict):
                return len(value) == 0
            return False

        checks: List[tuple[str, Any]] = []
        if output_schema_id == "swp_v1":
            checks = [
                ("tldr", payload.get("tldr")),
                ("decisions", payload.get("decisions")),
                ("open_questions", payload.get("open_questions")),
                ("next_actions", payload.get("next_actions")),
                ("risks", payload.get("risks")),
            ]
        elif output_schema_id == "esn_v1":
            ex = payload.get("example_from_sources", {}) if isinstance(payload.get("example_from_sources"), dict) else {}
            checks = [
                ("simple_explanation", payload.get("simple_explanation")),
                ("glossary", payload.get("glossary")),
                ("example_from_sources.example", ex.get("example")),
                ("common_pitfalls", payload.get("common_pitfalls")),
            ]
        elif output_schema_id == "skm_v1":
            checks = [
                ("patterns", payload.get("patterns")),
                ("outliers", payload.get("outliers")),
                ("hypotheses", payload.get("hypotheses")),
            ]

        total = len(checks)
        if total == 0:
            return 1.0, [], False
        present = 0
        for key, value in checks:
            if _is_empty(value):
                missing.append(key)
            else:
                present += 1
        score = float(present) / float(total)
        return score, missing, score < 0.5

    def build_narrative_answer(self, message: str, citations: List[Citation], strict_sources_only: bool) -> str:
        context = self._build_context(citations)
        if not context:
            return "Es gibt aktuell nicht genug Quellenbelege fuer eine verlaessliche Antwort. Bitte Filter lockern oder weitere Dokumente indexieren."

        strict_clause = (
            "Use only cited evidence from snippets. If uncertain, state uncertainty."
            if strict_sources_only
            else "Use snippets as primary evidence and keep uncertainty explicit."
        )
        prompt = (
            "You are a helpful knowledge assistant.\n"
            f"{strict_clause}\n"
            "Write a concise answer in German (max 6 sentences).\n"
            "Cite source IDs inline like [S1], [S2].\n"
            "If evidence is weak, clearly say what is missing.\n"
            f"User message: {message}\n\n"
            "Context:\n"
            f"{context}"
        )
        try:
            client = get_client()
            resp = client.chat.completions.create(
                model=LANGUAGE_MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
            )
            text = (resp.choices[0].message.content or "").strip()
            if text:
                return text
        except Exception:
            pass
        return "Die strukturierte Antwort ist unvollstaendig. Verfuegbare Quellen deuten auf Teilinformationen hin; bitte pruefe die Quellenliste fuer Details."

    def build_answer(
        self,
        output_schema_id: str,
        message: str,
        citations: List[Citation],
        strict_sources_only: bool,
    ) -> Tuple[Dict[str, Any], ModeValidationResult, float]:
        mode = self._SCHEMA_TO_MODE.get(output_schema_id)
        if mode is None:
            return {}, ModeValidationResult(schema_ok=False, errors=[f"Unknown schema id: {output_schema_id}"]), 0.0
        context = self._build_context(citations)
        if not context:
            return {}, ModeValidationResult(schema_ok=False, errors=["No sources available for answer synthesis."]), 0.0

        strict_clause = (
            "You must only use the provided source snippets. If evidence is missing, leave fields empty."
            if strict_sources_only
            else "Use the source snippets as primary evidence."
        )
        prompt = (
            "You are a knowledge assistant.\n"
            f"{strict_clause}\n"
            f"{PROMPT_BY_MODE[mode]}\n"
            "Use source IDs exactly as provided (S1, S2, ...).\n"
            "Context:\n"
            f"{context}\n\n"
            f"User message: {message}"
        )

        client = get_client()
        first = client.chat.completions.create(
            model=LANGUAGE_MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = first.choices[0].message.content or "{}"
        try:
            payload = self._try_parse_json(raw)
            data, validation = self._validate_mode_payload(mode, payload)
            if validation.schema_ok:
                allowed_source_ids = {c.sid for c in citations}
                source_id_errors = self._enforce_allowed_source_ids(data, allowed_source_ids)
                total, covered, invalid = self._collect_evidence_fields(data)
                if invalid:
                    source_id_errors.append(f"Invalid evidence format values: {invalid}")
                coverage = 0.0 if total == 0 else float(covered) / float(total)
                if strict_sources_only and source_id_errors:
                    return {}, ModeValidationResult(schema_ok=False, errors=source_id_errors), coverage
                if strict_sources_only and total > 0 and coverage == 0.0:
                    return {}, ModeValidationResult(schema_ok=False, errors=["Strict citation mode requires cited evidence fields."]), coverage
                return data, validation, coverage
            repair_prompt = (
                "Fix this JSON to match schema exactly and return JSON only.\n"
                f"Errors: {validation.errors}\n"
                f"JSON:\n{raw}"
            )
            second = client.chat.completions.create(
                model=LANGUAGE_MODEL_NAME,
                messages=[{"role": "user", "content": repair_prompt}],
            )
            repaired_raw = second.choices[0].message.content or "{}"
            repaired_payload = self._try_parse_json(repaired_raw)
            repaired_data, repaired_validation = self._validate_mode_payload(mode, repaired_payload)
            if not repaired_validation.schema_ok:
                return repaired_data, repaired_validation, 0.0
            allowed_source_ids = {c.sid for c in citations}
            source_id_errors = self._enforce_allowed_source_ids(repaired_data, allowed_source_ids)
            total, covered, invalid = self._collect_evidence_fields(repaired_data)
            if invalid:
                source_id_errors.append(f"Invalid evidence format values: {invalid}")
            coverage = 0.0 if total == 0 else float(covered) / float(total)
            if strict_sources_only and source_id_errors:
                return {}, ModeValidationResult(schema_ok=False, errors=source_id_errors), coverage
            return repaired_data, repaired_validation, coverage
        except Exception as exc:
            return {}, ModeValidationResult(schema_ok=False, errors=[f"JSON parse failed: {exc}"]), 0.0

    def explain_sources(self, citations: List[Citation]) -> List[str]:
        reasons = []
        for c in citations[:3]:
            reasons.append(f"{c.sid} selected due to high similarity and rerank relevance from {c.source}.")
        if not reasons:
            reasons.append("No citations were available for this request.")
        return reasons

    def map_role_phase_hint(self, mode: KnowledgeMode) -> str:
        if mode == KnowledgeMode.ESN:
            return "internalization"
        return "combination"

    def filters_to_domain(self, filters: Dict[str, Any]) -> ChatFilters:
        return ChatFilters(
            date_range_days=filters.get("date_range_days"),
            doctype=filters.get("doctype"),
            k=int(filters.get("k", 5)),
            mmr=bool(filters.get("mmr", False)),
        )
