from app.ui import artifacts as artifacts_module
from app.ui.artifacts import (
    _artifact_key,
    _format_artifact_card_header,
    _preview_text,
    collect_artifacts,
    collect_persisted_artifacts,
    merge_artifacts,
    parse_quiz_item,
)


def test_collect_artifacts_adds_turn_context():
    artifacts = collect_artifacts(
        [
            {
                "user": "Explain RAG",
                "payload": {
                    "role": "MentorAgent",
                    "artefacts": [
                        {
                            "type": "definition",
                            "title": "Definition",
                            "content": "A precise explanation.",
                            "concept_ids": [],
                        }
                    ],
                },
            }
        ]
    )

    assert artifacts == [
        {
            "type": "definition",
            "title": "Definition",
            "content": "A precise explanation.",
            "concept_ids": [],
            "_turn_index": 1,
            "_artifact_index": 1,
            "_role": "MentorAgent",
            "_user": "Explain RAG",
        }
    ]


def test_collect_artifacts_ignores_non_dict_artifacts():
    artifacts = collect_artifacts(
        [
            {
                "user": "Quiz me",
                "payload": {
                    "role": "MentorAgent",
                    "artefacts": ["not-an-artifact"],
                },
            }
        ]
    )

    assert artifacts == []


def test_preview_text_collapses_whitespace_and_truncates():
    preview = _preview_text("This   is\n\nlong " + "content " * 30, max_chars=30)

    assert preview == "This is long content conten..."
    assert len(preview) <= 30


def test_artifact_card_header_escapes_content():
    header = _format_artifact_card_header(
        title="<Definition>",
        artifact_type="definition",
        role="MentorAgent",
        turn_index=2,
        preview="<script>alert('x')</script>",
    )

    assert "&lt;Definition&gt;" in header
    assert "&lt;script&gt;" in header
    assert "ikmas-artifact-badge-definition" in header


def test_collect_persisted_artifacts_adds_saved_context(monkeypatch):
    monkeypatch.setattr(
        artifacts_module,
        "list_artefacts",
        lambda collection_id: [
            {
                "id": 1,
                "project": collection_id,
                "type": "definition",
                "title": "RAG",
                "content": "Retrieval augmented generation.",
                "created_at": "2026-06-06",
                "concept_ids": [],
            }
        ],
    )

    artifacts = collect_persisted_artifacts("team-space")

    assert artifacts[0]["id"] == 1
    assert artifacts[0]["_role"] == "Saved"
    assert artifacts[0]["_turn_index"] == "DB"


def test_merge_artifacts_dedupes_persisted_and_session_versions():
    persisted = [
        {
            "id": 1,
            "type": "definition",
            "title": "RAG",
            "content": "Retrieval augmented generation.",
        }
    ]
    session = [
        {
            "type": "definition",
            "title": "RAG",
            "content": "Retrieval augmented generation.",
            "_turn_index": 1,
        }
    ]

    merged = merge_artifacts(persisted, session)

    assert merged == persisted


def test_parse_quiz_item_from_formatted_content():
    quiz = parse_quiz_item(
        """
        Question: What is RAG?

        Options:
        A. Retrieval augmented generation
        B. Random answer generation

        Correct answer: A

        Explanation: RAG combines retrieval with generation.

        Evidence: Retrieval notes
        """
    )

    assert quiz == {
        "question": "What is RAG?",
        "options": [
            {"option": "A", "text": "Retrieval augmented generation"},
            {"option": "B", "text": "Random answer generation"},
        ],
        "correct_answer": "A",
        "explanation": "RAG combines retrieval with generation.",
        "evidence_reference": "Retrieval notes",
    }


def test_parse_quiz_item_from_json_content():
    quiz = parse_quiz_item(
        """{
          "question": "What is SECI?",
          "options": [
            {"option": "A", "text": "A knowledge conversion model"},
            {"option": "B", "text": "A storage engine"}
          ],
          "correct_answer": "A",
          "explanation": "SECI describes knowledge conversion.",
          "evidence_reference": "SECI notes"
        }"""
    )

    assert quiz is not None
    assert quiz["question"] == "What is SECI?"
    assert quiz["options"][0]["text"] == "A knowledge conversion model"


def test_artifact_key_differs_for_multiple_quizzes():
    first = {"title": "Quiz Item 1", "content": "Question: One", "_artifact_index": 1}
    second = {"title": "Quiz Item 2", "content": "Question: Two", "_artifact_index": 2}

    assert _artifact_key(first) != _artifact_key(second)
