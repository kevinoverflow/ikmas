from __future__ import annotations

import re
from typing import Any

from app.backend.workflow.task_models import AgentTaskResult


class ScribeWorkerBase:
    """Base class for Scribe worker agents."""

    def execute(self, task_spec: "TaskSpec", context: dict[str, Any]) -> AgentTaskResult:
        raise NotImplementedError("Subclasses must implement execute method")


def source_text_from_context(context: dict[str, Any]) -> str:
    parts: list[str] = []
    user_input = context.get("user_input")
    if isinstance(user_input, str) and user_input.strip():
        parts.append(user_input.strip())

    for turn in context.get("chat_history", []) or []:
        if isinstance(turn, dict):
            user_turn = turn.get("user")
            assistant_turn = turn.get("assistant")
            if isinstance(user_turn, str) and user_turn.strip():
                parts.append(user_turn.strip())
            if isinstance(assistant_turn, str) and assistant_turn.strip():
                parts.append(assistant_turn.strip())

    for chunk in context.get("retrieval_context", []) or []:
        if isinstance(chunk, dict):
            text = chunk.get("text")
            if isinstance(text, str) and text.strip():
                parts.append(text.strip())

    return "\n".join(parts)


def candidate_lines(text: str) -> list[str]:
    lines: list[str] = []
    for raw_line in text.splitlines():
        line = re.sub(r"^\s*[-*•\d.)]+\s*", "", raw_line).strip()
        if line:
            lines.append(line)
    if lines:
        return lines

    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return [sentence.strip() for sentence in sentences if sentence.strip()]


def matching_lines(text: str, keywords: tuple[str, ...]) -> list[str]:
    matches = []
    for line in candidate_lines(text):
        lowered = line.lower()
        if any(keyword in lowered for keyword in keywords):
            matches.append(line)
    return matches


def extract_numbered_concepts(text: str) -> list[str]:
    matches = re.findall(r"(?:^|[:,\n;]\s*)\d+\)\s*([^,\n;]+)", text)
    concepts = [match.strip(" .") for match in matches if match.strip(" .")]
    return concepts


def extract_markdown_headings(text: str) -> list[str]:
    headings = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            heading = stripped.lstrip("#").strip()
            if heading:
                headings.append(heading)
    return headings


def strip_label(line: str) -> str:
    return re.sub(
        r"^\s*(decision|decided|beschluss|assumption|annahme|issue|risk|open issue|open question|todo|action item|rationale)\s*[:\-]\s*",
        "",
        line,
        flags=re.IGNORECASE,
    ).strip()
