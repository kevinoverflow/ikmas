from __future__ import annotations

from typing import Any

from app.backend.workflow.task_models import AgentTaskResult
from app.backend.agents.workers.scribe_utils import (
    ScribeWorkerBase,
    extract_numbered_concepts,
    source_text_from_context,
)


class ScribeConceptSummaryWriter(ScribeWorkerBase):
    """Creates structured learning-summary shells for explicitly listed concepts."""

    def execute(self, task_spec: "TaskSpec", context: dict[str, Any]) -> AgentTaskResult:
        try:
            section = task_spec.input_scope.get("section", "")
            text = source_text_from_context(context)
            concepts = extract_numbered_concepts(text)

            summaries = []
            for concept in concepts:
                summaries.append(
                    {
                        "concept": concept,
                        "summary": (
                            f"Lernzusammenfassung zu {concept}. Ergänze die konkreten Inhalte "
                            "aus den Vorlesungsunterlagen, Fällen und Normen."
                        ),
                        "key_terms": [],
                        "legal_basis": [],
                        "assumptions": [
                            "Die Zusammenfassung muss anhand der verfügbaren Lehrveranstaltungsunterlagen validiert werden."
                        ],
                        "open_questions": [
                            "Welche konkreten Normen, Fälle und Prüfungsschemata wurden in der Lehrveranstaltung behandelt?"
                        ],
                        "reuse_guidance": (
                            "Als Wiederholungsblatt, Karteikartenbasis und Ausgangspunkt für Prüfungsschemata nutzbar."
                        ),
                        "confidence": "low" if not context.get("retrieval_context") else "medium",
                    }
                )

            return AgentTaskResult(
                task_id=task_spec.task_id,
                agent_role=task_spec.agent_role,
                status="success",
                output={
                    "learning_summaries": summaries,
                    "section": section,
                },
            )
        except Exception as e:
            return AgentTaskResult(
                task_id=task_spec.task_id,
                agent_role=task_spec.agent_role,
                status="failed",
                error=str(e),
            )
