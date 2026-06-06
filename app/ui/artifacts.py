from __future__ import annotations

import json
from html import escape
from typing import Any

import streamlit as st

from app.backend.artifact_actions import (
    delete_artifact,
    regenerate_artifact,
    save_artifact_edits,
)
from app.backend.sqlite_store import list_artefacts


ARTIFACT_TYPE_LABELS = {
    "definition": "Definition",
    "concept": "Concept",
    "quiz_item": "Quiz",
    "summary": "Summary",
    "flashcards": "Flashcards",
    "quiz": "Quiz",
    "checklist": "Checklist",
    "note": "Note",
    "concept_map": "Concept Map",
}

ARTIFACT_TYPE_CLASSES = {
    "definition": "definition",
    "concept": "concept",
    "quiz_item": "quiz",
    "quiz": "quiz",
    "summary": "summary",
    "concept_map": "concept",
}


def collect_artifacts(chat_history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    artifacts: list[dict[str, Any]] = []

    for turn_index, turn in enumerate(chat_history, start=1):
        payload = turn.get("payload", {})
        for artifact_index, artifact in enumerate(payload.get("artefacts", []), start=1):
            if not isinstance(artifact, dict):
                continue
            artifacts.append(
                {
                    **artifact,
                    "_turn_index": turn_index,
                    "_artifact_index": artifact_index,
                    "_role": payload.get("role", "Assistant"),
                    "_user": turn.get("user", ""),
                }
            )

    return artifacts


def collect_persisted_artifacts(collection_id: str) -> list[dict[str, Any]]:
    artifacts: list[dict[str, Any]] = []
    for artifact in list_artefacts(collection_id):
        artifacts.append(
            {
                **artifact,
                "_role": "Saved",
                "_turn_index": "DB",
                "_user": "",
            }
        )
    return artifacts


def merge_artifacts(
    persisted_artifacts: list[dict[str, Any]],
    session_artifacts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen: set[tuple[Any, str, str, str]] = set()

    for artifact in persisted_artifacts + session_artifacts:
        key = (
            artifact.get("id"),
            str(artifact.get("type") or ""),
            str(artifact.get("title") or ""),
            str(artifact.get("content") or ""),
        )
        fallback_key = (
            None,
            str(artifact.get("type") or ""),
            str(artifact.get("title") or ""),
            str(artifact.get("content") or ""),
        )
        if key in seen or fallback_key in seen:
            continue
        seen.add(key)
        seen.add(fallback_key)
        merged.append(artifact)

    return merged


def render_artifact_browser(collection_id: str, chat_history: list[dict[str, Any]]) -> None:
    _inject_artifact_browser_styles()
    try:
        persisted_artifacts = collect_persisted_artifacts(collection_id)
    except Exception as exc:
        persisted_artifacts = []
        load_error = str(exc)
    else:
        load_error = ""
    artifacts = merge_artifacts(persisted_artifacts, collect_artifacts(chat_history))

    with st.container(border=True):
        st.markdown("### Artifacts")
        if load_error:
            st.caption(f"Could not load saved artifacts: {load_error}")

        if not artifacts:
            st.caption("No artifacts generated yet.")
            return

        artifact_types = sorted({str(artifact.get("type", "unknown")) for artifact in artifacts})
        selected_type = st.selectbox(
            "Filter artifacts",
            ["All"] + artifact_types,
            key="artifact_browser_type_filter",
            label_visibility="collapsed",
        )

        filtered = [
            artifact
            for artifact in artifacts
            if selected_type == "All" or artifact.get("type") == selected_type
        ]

        st.caption(f"{len(filtered)} of {len(artifacts)} artifact{'s' if len(artifacts) != 1 else ''}")

        for artifact in reversed(filtered):
            _render_artifact_item(artifact)


def _render_artifact_item(artifact: dict[str, Any]) -> None:
    title = str(artifact.get("title") or "Untitled artifact")
    artifact_type = str(artifact.get("type") or "unknown")
    role = str(artifact.get("_role") or "Assistant")
    turn_index = artifact.get("_turn_index")
    content = str(artifact.get("content") or "")
    user_prompt = str(artifact.get("_user") or "")
    quiz_item = parse_quiz_item(content) if artifact_type == "quiz_item" else None
    display_title = quiz_item["question"] if quiz_item else title
    preview = _quiz_preview(quiz_item) if quiz_item else _preview_text(content)

    st.markdown(
        _format_artifact_card_header(
            title=display_title,
            artifact_type=artifact_type,
            role=role,
            turn_index=turn_index,
            preview=preview,
        ),
        unsafe_allow_html=True,
    )

    if quiz_item:
        _render_quiz_item(artifact, quiz_item, user_prompt, display_title)
        return

    with st.expander("Open artifact"):
        if user_prompt:
            st.caption(f"Prompt: {user_prompt}")
        st.write(content)
        _render_artifact_actions(
            artifact=artifact,
            default_title=title,
            default_content=content,
        )


def parse_quiz_item(content: str) -> dict[str, Any] | None:
    parsed = _parse_quiz_json(content)
    if parsed is not None:
        return parsed

    sections = _parse_labeled_sections(content)
    question = sections.get("question", "").strip()
    options_block = sections.get("options", "").strip()
    correct_answer = sections.get("correct answer", "").strip()

    options = _parse_option_lines(options_block)
    if not question or not options or not correct_answer:
        return None

    return {
        "question": question,
        "options": options,
        "correct_answer": correct_answer,
        "explanation": sections.get("explanation", "").strip(),
        "evidence_reference": sections.get("evidence", "").strip(),
    }


def _parse_quiz_json(content: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None

    if "quiz_items" in parsed and isinstance(parsed["quiz_items"], list) and parsed["quiz_items"]:
        first_item = parsed["quiz_items"][0]
        parsed = first_item if isinstance(first_item, dict) else {}

    question = parsed.get("question")
    options = parsed.get("options")
    correct_answer = parsed.get("correct_answer")
    if not isinstance(question, str) or not isinstance(options, list) or not isinstance(correct_answer, str):
        return None

    normalized_options: list[dict[str, str]] = []
    for option in options:
        if not isinstance(option, dict):
            continue
        label = option.get("option")
        text = option.get("text")
        if isinstance(label, str) and isinstance(text, str):
            normalized_options.append({"option": label.strip(), "text": text.strip()})

    if not normalized_options:
        return None

    return {
        "question": question.strip(),
        "options": normalized_options,
        "correct_answer": correct_answer.strip(),
        "explanation": str(parsed.get("explanation") or "").strip(),
        "evidence_reference": str(parsed.get("evidence_reference") or parsed.get("evidence") or "").strip(),
    }


def _parse_labeled_sections(content: str) -> dict[str, str]:
    labels = {
        "question",
        "options",
        "correct answer",
        "explanation",
        "evidence",
    }
    sections: dict[str, list[str]] = {}
    current_label: str | None = None

    for raw_line in content.splitlines():
        line = raw_line.strip()
        lowered = line.lower()
        matched_label = None
        matched_value = ""
        for label in labels:
            prefix = f"{label}:"
            if lowered.startswith(prefix):
                matched_label = label
                matched_value = line[len(prefix):].strip()
                break

        if matched_label is not None:
            current_label = matched_label
            sections.setdefault(current_label, [])
            if matched_value:
                sections[current_label].append(matched_value)
            continue

        if current_label and line:
            sections[current_label].append(line)

    return {label: "\n".join(lines) for label, lines in sections.items()}


def _parse_option_lines(options_block: str) -> list[dict[str, str]]:
    options: list[dict[str, str]] = []
    for raw_line in options_block.splitlines():
        line = raw_line.strip()
        if len(line) < 3:
            continue
        label = line[0]
        separator = line[1]
        if not label.isalpha() or separator not in {".", ")"}:
            continue
        text = line[2:].strip()
        if text:
            options.append({"option": label.upper(), "text": text})
    return options


def _quiz_preview(quiz_item: dict[str, Any]) -> str:
    return f"{len(quiz_item['options'])} choices · check your answer"


def _render_quiz_item(
    artifact: dict[str, Any],
    quiz_item: dict[str, Any],
    user_prompt: str,
    display_title: str,
) -> None:
    key_base = _artifact_key(artifact)
    option_labels = [
        f"{option['option']}. {option['text']}"
        for option in quiz_item["options"]
    ]
    selected = st.radio(
        "Choose an answer",
        option_labels,
        key=f"quiz_choice::{key_base}",
        label_visibility="collapsed",
    )
    if st.button("Check answer", key=f"quiz_check::{key_base}", use_container_width=True):
        st.session_state[f"quiz_checked::{key_base}"] = selected

    checked = st.session_state.get(f"quiz_checked::{key_base}")
    if checked:
        selected_label = checked.split(".", 1)[0].strip()
        correct_label = str(quiz_item["correct_answer"]).strip()
        if selected_label.lower() == correct_label.lower():
            st.success("Correct.")
        else:
            st.error(f"Not quite. Correct answer: {correct_label}.")

    with st.expander("Explanation and evidence"):
        if user_prompt:
            st.caption(f"Prompt: {user_prompt}")
        explanation = quiz_item.get("explanation")
        evidence = quiz_item.get("evidence_reference")
        if explanation:
            st.markdown(f"**Explanation:** {explanation}")
        if evidence:
            st.markdown(f"**Evidence:** {evidence}")
        _render_artifact_actions(
            artifact=artifact,
            default_title=display_title,
            default_content=str(artifact.get("content") or ""),
        )


def _render_artifact_actions(
    *,
    artifact: dict[str, Any],
    default_title: str,
    default_content: str,
) -> None:
    artifact_id = artifact.get("id")
    if artifact_id is None:
        st.caption("Edit, delete, and regenerate are available after this artifact is saved.")
        return

    key_base = _artifact_key(artifact)
    st.divider()
    st.caption("Manage artifact")

    edited_title = st.text_input(
        "Title",
        value=default_title,
        key=f"artifact_title::{key_base}",
    )
    edited_content = st.text_area(
        "Content",
        value=default_content,
        height=220,
        key=f"artifact_content::{key_base}",
    )

    save_col, regenerate_col, delete_col = st.columns([1, 1, 1])
    if save_col.button("Save", key=f"artifact_save::{key_base}", use_container_width=True):
        if save_artifact_edits(
            artefact_id=int(artifact_id),
            title=edited_title,
            content=edited_content,
        ):
            st.success("Artifact saved.")
            st.rerun()
        st.error("Artifact could not be saved.")

    if regenerate_col.button("Regenerate", key=f"artifact_regenerate::{key_base}", use_container_width=True):
        try:
            with st.spinner("Regenerating artifact..."):
                regenerate_artifact(artefact_id=int(artifact_id))
        except Exception as exc:
            st.error(f"Regeneration failed: {exc}")
        else:
            st.success("Artifact regenerated.")
            st.rerun()

    confirm_delete = st.checkbox(
        "Confirm delete",
        key=f"artifact_delete_confirm::{key_base}",
    )
    if delete_col.button(
        "Delete",
        key=f"artifact_delete::{key_base}",
        use_container_width=True,
        disabled=not confirm_delete,
    ):
        if delete_artifact(artefact_id=int(artifact_id)):
            st.success("Artifact deleted.")
            st.rerun()
        st.error("Artifact could not be deleted.")


def _artifact_key(artifact: dict[str, Any]) -> str:
    stable_parts = [
        str(artifact.get("id") or ""),
        str(artifact.get("_turn_index") or ""),
        str(artifact.get("_artifact_index") or ""),
        str(artifact.get("title") or ""),
        str(artifact.get("content") or "")[:80],
    ]
    return str(abs(hash("::".join(stable_parts))))


def _format_artifact_card_header(
    *,
    title: str,
    artifact_type: str,
    role: str,
    turn_index: Any,
    preview: str,
) -> str:
    label = ARTIFACT_TYPE_LABELS.get(artifact_type, artifact_type.replace("_", " ").title())
    css_class = ARTIFACT_TYPE_CLASSES.get(artifact_type, "default")
    safe_title = escape(title)
    safe_label = escape(label)
    safe_role = escape(role)
    safe_turn = escape(str(turn_index))
    safe_preview = escape(preview)

    return f"""
    <div class="ikmas-artifact-card">
        <div class="ikmas-artifact-card-top">
            <span class="ikmas-artifact-badge ikmas-artifact-badge-{css_class}">{safe_label}</span>
            <span class="ikmas-artifact-meta">Turn {safe_turn} · {safe_role}</span>
        </div>
        <div class="ikmas-artifact-title">{safe_title}</div>
        <div class="ikmas-artifact-preview">{safe_preview}</div>
    </div>
    """


def _preview_text(content: str, max_chars: int = 150) -> str:
    text = " ".join(content.split())
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."


def _inject_artifact_browser_styles() -> None:
    st.markdown(
        """
        <style>
        section.main div[data-testid="column"]:last-child div[data-testid="stVerticalBlockBorderWrapper"] {
            position: sticky;
            top: 1rem;
        }

        .ikmas-artifact-card {
            background: #ffffff;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.05);
            margin-top: 0.75rem;
            padding: 0.75rem;
        }

        .ikmas-artifact-card-top {
            align-items: center;
            display: flex;
            gap: 0.5rem;
            justify-content: space-between;
            margin-bottom: 0.45rem;
        }

        .ikmas-artifact-badge {
            border-radius: 999px;
            border: 1px solid #d1d5db;
            color: #111827;
            display: inline-flex;
            flex: 0 0 auto;
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0;
            line-height: 1;
            padding: 0.28rem 0.48rem;
        }

        .ikmas-artifact-badge-definition {
            background: #eef6ff;
            border-color: #bfdbfe;
            color: #1d4ed8;
        }

        .ikmas-artifact-badge-concept {
            background: #ecfdf5;
            border-color: #bbf7d0;
            color: #047857;
        }

        .ikmas-artifact-badge-quiz {
            background: #fff7ed;
            border-color: #fed7aa;
            color: #c2410c;
        }

        .ikmas-artifact-badge-summary {
            background: #f5f3ff;
            border-color: #ddd6fe;
            color: #6d28d9;
        }

        .ikmas-artifact-badge-default {
            background: #f9fafb;
            border-color: #e5e7eb;
            color: #374151;
        }

        .ikmas-artifact-meta {
            color: #6b7280;
            flex: 1 1 auto;
            font-size: 0.72rem;
            line-height: 1.2;
            min-width: 0;
            overflow-wrap: anywhere;
            text-align: right;
        }

        .ikmas-artifact-title {
            color: #111827;
            font-size: 0.95rem;
            font-weight: 700;
            line-height: 1.25;
            overflow-wrap: anywhere;
        }

        .ikmas-artifact-preview {
            color: #4b5563;
            font-size: 0.82rem;
            line-height: 1.4;
            margin-top: 0.35rem;
            overflow-wrap: anywhere;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
