from typing import Any

from app.backend.workflow.task_models import AgentTaskResult
from app.backend.agents.workers.scribe_utils import ScribeWorkerBase, matching_lines, source_text_from_context, strip_label

class ScribeDecisionExtractor(ScribeWorkerBase):
    """Extracts decisions from input."""
    
    def execute(self, task_spec: "TaskSpec", context: dict[str, Any]) -> AgentTaskResult:
        try:
            section = task_spec.input_scope.get("section", "")
            text = source_text_from_context(context)
            lines = matching_lines(
                text,
                (
                    "decision",
                    "decided",
                    "agreed",
                    "beschluss",
                    "entschieden",
                    "we will",
                    "we chose",
                ),
            )

            decisions = []
            for line in lines:
                decisions.append(
                    {
                        "decision": strip_label(line),
                        "rationale": "Extracted from explicit decision wording in the input.",
                        "stakeholders": [],
                        "confidence": "medium",
                    }
                )
            
            return AgentTaskResult(
                task_id=task_spec.task_id,
                agent_role=task_spec.agent_role,
                status="success",
                output={
                    "decisions": decisions,
                    "section": section
                }
            )
        except Exception as e:
            return AgentTaskResult(
                task_id=task_spec.task_id,
                agent_role=task_spec.agent_role,
                status="failed",
                error=str(e)
            )
