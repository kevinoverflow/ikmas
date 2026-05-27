from typing import Any

from app.backend.workflow.task_models import AgentTaskResult
from app.backend.agents.workers.scribe_utils import ScribeWorkerBase, matching_lines, source_text_from_context, strip_label

class ScribeIssueExtractor(ScribeWorkerBase):
    """Extracts open issues from input."""
    
    def execute(self, task_spec: "TaskSpec", context: dict[str, Any]) -> AgentTaskResult:
        try:
            section = task_spec.input_scope.get("section", "")
            text = source_text_from_context(context)
            lines = matching_lines(
                text,
                (
                    "issue",
                    "risk",
                    "open",
                    "question",
                    "todo",
                    "action",
                    "blocked",
                    "unclear",
                    "problem",
                ),
            )
            
            open_issues = [
                {
                    "issue": strip_label(line),
                    "description": "Extracted from issue, risk, question, or action wording in the input.",
                    "priority": "medium",
                    "owner": None,
                }
                for line in lines
            ]
            
            return AgentTaskResult(
                task_id=task_spec.task_id,
                agent_role=task_spec.agent_role,
                status="success",
                output={
                    "open_issues": open_issues,
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
