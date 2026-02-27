from fastapi.testclient import TestClient

from app.api import main as api_main
from app.domain.types import RetrievalResult, UserModelSnapshot
from app.infrastructure import db
from app.rag import storage


def test_upload_dedupe_and_list(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "UPLOAD_DIR", tmp_path / "uploads")
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "ikmas_test.db")
    db.init_db()

    client = TestClient(api_main.app)

    files = [("files", ("doc.pdf", b"abc", "application/pdf"))]
    r1 = client.post("/v1/files/upload?collection_id=default&on_name_conflict=skip", files=files)
    assert r1.status_code == 200
    assert r1.json()["stats"]["saved"] == 1

    files_same = [("files", ("doc-copy.pdf", b"abc", "application/pdf"))]
    r2 = client.post("/v1/files/upload?collection_id=default&on_name_conflict=skip", files=files_same)
    assert r2.status_code == 200
    assert r2.json()["stats"]["skipped_identical"] == 1

    listed = client.get("/v1/files?collection_id=default")
    assert listed.status_code == 200
    assert len(listed.json()["files"]) == 1


def test_query_returns_routing_and_sources(monkeypatch):
    client = TestClient(api_main.app)

    monkeypatch.setattr(
        api_main.knowledge_service,
        "query",
        lambda **kwargs: RetrievalResult(
            answer="test answer",
            sources=[{"source": "s1", "page": 1, "content": "ctx", "rerank_score": 0.8}],
            confidence=0.8,
            retrieved_count=1,
        ),
    )
    monkeypatch.setattr(
        api_main.user_model_service,
        "get_snapshot",
        lambda user_id: UserModelSnapshot(user_id=user_id, knowledge_distance=0.2, learning_progress=0.4),
    )

    payload = {
        "collection_id": "default",
        "question": "Explain this",
        "chat_history": [],
        "user_id": "u1",
        "session_phase": "internalization",
        "k_retrieve": 30,
        "k_final": 5,
    }
    r = client.post("/v1/query", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["answer"] == "test answer"
    assert body["retrieved_count"] == 1
    assert body["role"] in {"tutor", "mentor", "simulation", "curator", "context_restoration"}


def test_projects_and_documents_endpoints(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "UPLOAD_DIR", tmp_path / "uploads")
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "ikmas_test.db")
    db.init_db()
    client = TestClient(api_main.app)

    create = client.post("/v1/projects", json={"name": "Alpha"})
    assert create.status_code == 200
    project_id = create.json()["id"]

    listed = client.get("/v1/projects")
    assert listed.status_code == 200
    assert any(p["id"] == project_id for p in listed.json())

    files = [("files", ("doc.pdf", b"abc", "application/pdf"))]
    up = client.post(f"/v1/upload?project_id={project_id}&conflict_mode=skip", files=files)
    assert up.status_code == 200
    assert up.json()["stats"]["saved"] == 1

    docs = client.get(f"/v1/documents?project_id={project_id}")
    assert docs.status_code == 200
    assert len(docs.json()["documents"]) >= 1


def test_chat_and_onboarding_contract(monkeypatch):
    client = TestClient(api_main.app)

    monkeypatch.setattr(
        api_main.project_service,
        "get_project",
        lambda project_id: {"id": project_id, "name": "P", "collection_id": "default"},
    )
    monkeypatch.setattr(
        api_main.retrieval_service,
        "retrieve",
        lambda collection_id, query, policy, filters: [],
    )
    monkeypatch.setattr(
        api_main.retrieval_service,
        "log_retrieval",
        lambda project_id, mode, query, filters, policy_applied: None,
    )
    monkeypatch.setattr(
        api_main.retrieval_service,
        "_merge_policy_and_filters",
        lambda policy, filters: {"k": 5, "mmr": False, "date_range_days": None, "doctype": None, "rerank_strategy": "balanced"},
    )
    monkeypatch.setattr(
        api_main.retrieval_service,
        "log_interaction",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        api_main.answer_service,
        "build_answer",
        lambda output_schema_id, message, citations, strict_sources_only: (
            {
                "tldr": "x",
                "decisions": [],
                "open_questions": [],
                "next_actions": [],
                "risks": [],
            },
            type("Validation", (), {"schema_ok": True, "errors": []})(),
            1.0,
        ),
    )
    monkeypatch.setattr(
        api_main.answer_service,
        "explain_sources",
        lambda citations: ["test"],
    )
    monkeypatch.setattr(
        api_main.user_model_service,
        "get_snapshot",
        lambda user_id: UserModelSnapshot(user_id=user_id, knowledge_distance=0.2, learning_progress=0.4),
    )

    payload = {
        "project_id": "p1",
        "mode_override": "AUTO",
        "message": "status",
        "filters": {"k": 5, "mmr": False},
        "strict_citations": True,
        "user_id": "u1",
    }
    r = client.post("/v1/chat", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] in {"SWP", "ESN", "SKM"}
    assert "data" in body
    assert "citations" in body
    assert "validation" in body
    assert "router" in body
    assert "policy_applied" in body["retrieval"]

    onboarding = client.post("/v1/onboarding", json={"project_id": "p1", "mode": "SWP"})
    assert onboarding.status_code == 200


def test_router_preview(monkeypatch):
    client = TestClient(api_main.app)
    monkeypatch.setattr(
        api_main.user_model_service,
        "get_snapshot",
        lambda user_id: UserModelSnapshot(user_id=user_id, knowledge_distance=0.2, learning_progress=0.4),
    )
    resp = client.post(
        "/v1/router/preview",
        json={"message": "Explain this topic", "mode_override": "AUTO", "retrieval_confidence": 0.4},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["mode_distance"] in {"SWP", "ESN", "SKM"}
    assert body["output_schema_id"] in {"swp_v1", "esn_v1", "skm_v1"}
