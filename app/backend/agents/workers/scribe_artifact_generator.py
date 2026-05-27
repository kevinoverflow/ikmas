from __future__ import annotations

import json
from typing import Any

from app.backend.workflow.task_models import AgentTaskResult
from app.backend.agents.workers.scribe_utils import (
    ScribeWorkerBase,
    candidate_lines,
    extract_markdown_headings,
    extract_numbered_concepts,
    source_text_from_context,
)


VALID_ARTEFACT_TYPES = {"summary", "flashcards", "quiz", "checklist", "note", "concept_map"}


class ScribeArtifactGenerator(ScribeWorkerBase):
    """Creates persisted study/work artefacts selected by the workflow planner."""

    def execute(self, task_spec: "TaskSpec", context: dict[str, Any]) -> AgentTaskResult:
        try:
            artifact_type = str(task_spec.input_scope.get("artifact_type") or "summary")
            if artifact_type not in VALID_ARTEFACT_TYPES:
                artifact_type = "summary"

            text = source_text_from_context(context)
            concepts = extract_markdown_headings(text) or extract_numbered_concepts(text)
            if not concepts:
                concepts = [
                    line.strip(" -:")
                    for line in candidate_lines(text)
                    if 3 <= len(line.strip()) <= 120 and not line.strip().startswith("```")
                ][:20]

            title = str(task_spec.input_scope.get("title") or f"Generated {artifact_type.title()}")
            content = self._build_content(artifact_type, concepts, text)

            return AgentTaskResult(
                task_id=task_spec.task_id,
                agent_role=task_spec.agent_role,
                status="success",
                output={
                    "artefacts": [
                        {
                            "type": artifact_type,
                            "title": title,
                            "content": content,
                            "concept_ids": [],
                        }
                    ],
                    "section": task_spec.input_scope.get("section", artifact_type),
                },
            )
        except Exception as e:
            return AgentTaskResult(
                task_id=task_spec.task_id,
                agent_role=task_spec.agent_role,
                status="failed",
                error=str(e),
            )

    def _build_content(self, artifact_type: str, concepts: list[str], text: str) -> str:
        concepts = concepts[:30]
        if artifact_type == "flashcards":
            cards = [
                {
                    "front": concept,
                    "back": (
                        f"Erkläre {concept}: Definition, zentrale Voraussetzungen, wichtige Normen "
                        "und typische Prüfungsfrage anhand der Quellen wiederholen."
                    ),
                }
                for concept in concepts
            ]
            return json.dumps(cards, ensure_ascii=False, indent=2)

        if artifact_type == "quiz":
            questions = [
                {
                    "question": f"Welche zentrale Bedeutung hat {concept}?",
                    "answer": f"{concept} anhand der Unterlagen definieren und in den Prüfungsaufbau einordnen.",
                }
                for concept in concepts
            ]
            return json.dumps(questions, ensure_ascii=False, indent=2)

        if artifact_type == "checklist":
            return "\n".join(f"- {concept}: Definition, Voraussetzungen, Rechtsfolge, Prüfungspunkt" for concept in concepts)

        if artifact_type == "concept_map":
            return "\n".join(f"- {concept}" for concept in concepts)

        if artifact_type == "note":
            return "\n\n".join(concepts) if concepts else text[:4000]

        return "\n".join(f"## {concept}\nKurzdefinition, Kernelemente, Rechtsgrundlagen und Wiederverwendung ergänzen." for concept in concepts) or text[:4000]
