from app.backend import artifact_actions


def test_save_artifact_edits_trims_and_delegates(monkeypatch):
    seen = {}

    def fake_update(artefact_id, *, title, content):
        seen["args"] = (artefact_id, title, content)
        return True

    monkeypatch.setattr(artifact_actions, "update_artefact", fake_update)

    assert artifact_actions.save_artifact_edits(
        artefact_id=7,
        title="  Updated  ",
        content="  Better content  ",
    )
    assert seen["args"] == (7, "Updated", "Better content")


def test_delete_artifact_delegates(monkeypatch):
    seen = {}

    def fake_delete(artefact_id):
        seen["id"] = artefact_id
        return True

    monkeypatch.setattr(artifact_actions, "delete_artefact", fake_delete)

    assert artifact_actions.delete_artifact(artefact_id=9)
    assert seen["id"] == 9


def test_regenerate_artifact_updates_with_specific_generator_result(monkeypatch):
    seen = {}
    retrieval_calls = []

    monkeypatch.setattr(
        artifact_actions,
        "get_artefact",
        lambda artefact_id: {
            "id": artefact_id,
            "project": "team-space",
            "type": "definition",
            "title": "RAG",
            "content": "Old definition",
            "created_at": "2026-06-06",
            "concept_ids": [],
        },
    )
    monkeypatch.setattr(
        artifact_actions,
        "list_artefacts",
        lambda project, limit=100: [
            {
                "id": 4,
                "project": project,
                "type": "concept",
                "title": "Retriever",
                "content": "Related concept detail",
                "created_at": "2026-06-06",
                "concept_ids": [],
            }
        ],
    )

    def fake_retrieval(*, query, collection_name, k_retrieve, k_final):
        retrieval_calls.append((query, collection_name, k_retrieve, k_final))
        return {
            "chunks": [
                {
                    "text": "Detailed source chunk about retrieval augmented generation.",
                }
            ]
        }

    monkeypatch.setattr(artifact_actions, "run_retrieval", fake_retrieval)

    def fake_update(artefact_id, *, title, content):
        seen["updated"] = (artefact_id, title, content)
        return True

    class FakeBackend:
        def generate(self, prompt, **kwargs):
            seen["prompt"] = prompt
            return '{"definitions": [{"title": "RAG", "definition": "New definition", "scope": "Project use"}]}'

    monkeypatch.setattr(artifact_actions, "update_artefact", fake_update)

    regenerated = artifact_actions.regenerate_artifact(
        artefact_id=3,
        backend=FakeBackend(),
    )

    assert regenerated["title"] == "RAG"
    assert "New definition" in regenerated["content"]
    assert seen["updated"] == (3, "RAG", "New definition\n\nScope: Project use")
    assert retrieval_calls[0][1] == "team-space"
    assert "Detailed source chunk" in seen["prompt"]
    assert "Related concept detail" in seen["prompt"]


def test_regeneration_context_falls_back_when_retrieval_fails(monkeypatch):
    artifact = {
        "id": 3,
        "project": "team-space",
        "type": "note",
        "title": "Legacy note",
        "content": "Existing note content",
        "created_at": "2026-06-06",
        "concept_ids": [],
    }

    monkeypatch.setattr(
        artifact_actions,
        "run_retrieval",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("retrieval unavailable")),
    )
    monkeypatch.setattr(artifact_actions, "list_artefacts", lambda *args, **kwargs: [])

    context = artifact_actions._build_regeneration_context(artifact)

    assert "Existing note content" in context
    assert "Source context from the knowledge base" not in context
