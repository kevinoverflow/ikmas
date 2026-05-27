from typing import Any

from app.backend.workflow.task_models import AgentTaskResult
from app.backend.agents.workers.scribe_utils import ScribeWorkerBase, matching_lines, source_text_from_context, strip_label

class ScribeAssumptionExtractor(ScribeWorkerBase):
    """Extracts assumptions from input."""
    
    def execute(self, task_spec: "TaskSpec", context: dict[str, Any]) -> AgentTaskResult:
        try:
            section = task_spec.input_scope.get("section", "")
            text = source_text_from_context(context)
            lines = matching_lines(
                text,
                (
                    "assumption",
                    "assume",
                    "assuming",
                    "annahme",
                    "constraint",
                    "dependency",
                    "depends on",
                    "provided that",
                    "if ",
                ),
            )
            
            assumptions = [
                {
                    "assumption": strip_label(line),
                    "justification": "Extracted from assumption, constraint, or dependency wording in the input.",
                    "confidence": "medium",
                }
                for line in lines
            ]
            
            return AgentTaskResult(
                task_id=task_spec.task_id,
                agent_role=task_spec.agent_role,
                status="success",
                output={
                    "assumptions": assumptions,
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
