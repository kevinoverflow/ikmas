from app.backend import artifact_reuse_agent as reuse_module
from app.backend.artifact_reuse_agent import ArtifactReuseAgent


def test_artifact_reuse_agent_reuses_similar_artifacts(monkeypatch):
    monkeypatch.setattr(
        reuse_module,
        "find_similar_artefacts",
        lambda **kwargs: [
            {
                "id": 1,
                "type": "definition",
                "title": "RAG",
                "content": "Retrieval augmented generation combines retrieval and generation.",
            }
        ],
    )

    decision = ArtifactReuseAgent().find_reusable_artifacts(
        project="team-space",
        user_input="Define RAG",
        artifact_types=["definition"],
    )

    assert decision.reused_artifacts[0]["id"] == 1
    assert decision.missing_artifact_types == []


def test_artifact_reuse_agent_can_partially_reuse_and_still_generate_missing(monkeypatch):
    monkeypatch.setattr(
        reuse_module,
        "find_similar_artefacts",
        lambda **kwargs: [
            {
                "id": 1,
                "type": "definition",
                "title": "RAG",
                "content": "Retrieval augmented generation combines retrieval and generation.",
            }
        ],
    )

    decision = ArtifactReuseAgent().find_reusable_artifacts(
        project="team-space",
        user_input="Define RAG",
        artifact_types=["definition"],
        desired_counts={"definition": 3},
    )

    assert decision.reused_artifacts[0]["id"] == 1
    assert decision.missing_artifact_types == ["definition"]


def test_artifact_reuse_agent_marks_missing_when_no_match(monkeypatch):
    monkeypatch.setattr(
        reuse_module,
        "find_similar_artefacts",
        lambda **kwargs: [
            {
                "id": 2,
                "type": "definition",
                "title": "Unrelated",
                "content": "Something else entirely.",
            }
        ],
    )

    decision = ArtifactReuseAgent().find_reusable_artifacts(
        project="team-space",
        user_input="Define RAG",
        artifact_types=["definition"],
    )

    assert decision.reused_artifacts == []
    assert decision.missing_artifact_types == ["definition"]
