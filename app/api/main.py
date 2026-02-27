from __future__ import annotations

import json
import time
from typing import List

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse

from app.api.schemas import (
    AssessmentRequest,
    ChatRequest,
    ChatResponse,
    CitationResponse,
    IndexRebuildRequest,
    OnboardingRequest,
    PracticeRequest,
    ProjectCreateRequest,
    ProjectResponse,
    QueryRequest,
    QueryResponse,
    RetrievalPolicyResponse,
    RouterInfoResponse,
    RouterPreviewRequest,
    SessionEventRequest,
    StartSessionRequest,
    ValidationInfo,
)
from app.domain.types import Citation, SECIPhase
from app.infrastructure.db import init_db
from app.rag.storage import delete_file, get_file_path, list_collection_files
from app.services.answer_service import AnswerService
from app.services.document_service import DocumentService
from app.services.knowledge_service import KnowledgeService
from app.services.project_service import ProjectService
from app.services.retrieval_service import RetrievalService
from app.services.role_router_service import RoleRouterService
from app.services.seci_workflow_service import SECIWorkflowService
from app.services.tutoring_service import TutoringService
from app.services.user_model_service import UserModelService

app = FastAPI(title="IKMAS API", version="0.2.0")

project_service = ProjectService()
knowledge_service = KnowledgeService()
document_service = DocumentService(project_service=project_service)
retrieval_service = RetrievalService()
answer_service = AnswerService()
user_model_service = UserModelService()
role_router_service = RoleRouterService()
seci_service = SECIWorkflowService()
tutoring_service = TutoringService(user_model_service=user_model_service)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    project_service.ensure_default_project()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


def _citations_from_docs(docs: list) -> List[Citation]:
    citations: List[Citation] = []
    for idx, d in enumerate(docs, start=1):
        md = d.metadata or {}
        citations.append(
            Citation(
                sid=f"S{idx}",
                source=str(md.get("source", "Uploaded PDF")),
                page=md.get("page"),
                chunk_id=str(md.get("chunk_id", f"chunk-{idx}")),
                snippet=d.page_content[:500],
                metadata=md,
            )
        )
    return citations


@app.post("/v1/projects", response_model=ProjectResponse)
def create_project(req: ProjectCreateRequest) -> ProjectResponse:
    try:
        return ProjectResponse(**project_service.create_project(req.name))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/v1/projects", response_model=List[ProjectResponse])
def list_projects() -> List[ProjectResponse]:
    return [ProjectResponse(**p) for p in project_service.list_projects()]


@app.get("/v1/files")
def list_files(collection_id: str = Query(default="default")) -> dict:
    files = list_collection_files(collection_id)
    return {
        "collection_id": collection_id,
        "files": [
            {
                "name": f.path.name,
                "size_bytes": f.size_bytes,
                "sha256": f.sha256,
            }
            for f in files
        ],
    }


@app.get("/v1/files/{filename}/download")
def download_file(filename: str, collection_id: str = Query(default="default")) -> StreamingResponse:
    path = get_file_path(collection_id, filename)
    if path is None:
        raise HTTPException(status_code=404, detail="File not found.")
    return StreamingResponse(
        iter([path.read_bytes()]),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{path.name}"'},
    )


@app.delete("/v1/files/{filename}")
def remove_file(filename: str, collection_id: str = Query(default="default")) -> dict:
    deleted = delete_file(collection_id, filename)
    if not deleted:
        raise HTTPException(status_code=404, detail="File not found.")
    return {"deleted": True, "filename": filename}


@app.post("/v1/files/upload")
async def upload_files(
    files: List[UploadFile] = File(...),
    collection_id: str = Query(default="default"),
    on_name_conflict: str = Query(default="skip"),
) -> dict:
    packed = []
    for file in files:
        packed.append((file.filename, await file.read()))
    stats = knowledge_service.upload_files(
        collection_id=collection_id,
        files=packed,
        on_name_conflict=on_name_conflict,
    )
    return {"collection_id": collection_id, "stats": stats}


@app.post("/v1/upload")
async def upload_project_files(
    files: List[UploadFile] = File(...),
    project_id: str = Query(...),
    conflict_mode: str = Query(default="skip"),
) -> dict:
    packed = []
    for file in files:
        packed.append((file.filename, await file.read()))
    try:
        stats = document_service.upload_files(project_id, packed, on_name_conflict=conflict_mode)
        return {"project_id": project_id, "stats": stats}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/v1/documents")
def list_documents(project_id: str = Query(...)) -> dict:
    try:
        return {"project_id": project_id, "documents": document_service.list_documents(project_id)}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.delete("/v1/documents/{doc_id}")
def delete_document_endpoint(doc_id: str) -> dict:
    if not document_service.delete_document(doc_id):
        raise HTTPException(status_code=404, detail="Document not found.")
    return {"deleted": True, "doc_id": doc_id}


@app.post("/v1/index/rebuild")
def rebuild_index(req: IndexRebuildRequest) -> dict:
    if req.project_id:
        indexed_chunks = document_service.rebuild_index(req.project_id, req.reindex)
        return {"project_id": req.project_id, "indexed_chunks": indexed_chunks}
    indexed_chunks = knowledge_service.rebuild_index(req.collection_id, req.reindex)
    return {"collection_id": req.collection_id, "indexed_chunks": indexed_chunks}


@app.post("/v1/query", response_model=QueryResponse)
def query(req: QueryRequest) -> QueryResponse:
    retrieval = knowledge_service.query(
        collection_id=req.collection_id,
        question=req.question,
        chat_history=req.chat_history,
        k_retrieve=req.k_retrieve,
        k_final=req.k_final,
    )
    user_model = user_model_service.get_snapshot(req.user_id)
    decision = role_router_service.route(
        message=req.question,
        mode_override=None,
        retrieval_signals={"retrieval_confidence": retrieval.confidence},
        user_model=user_model,
        session_phase=req.session_phase,
    )
    return QueryResponse(
        answer=retrieval.answer,
        sources=retrieval.sources,
        retrieval_confidence=retrieval.confidence,
        retrieved_count=retrieval.retrieved_count,
        role=decision.role.value,
        routing_reason=decision.reason,
        routing_confidence=decision.confidence,
    )


def _chat_impl(req: ChatRequest) -> ChatResponse:
    started = time.perf_counter()
    project = project_service.get_project(req.project_id)
    strict_citations = req.strict_citations if req.strict_citations is not None else req.strict_sources_only
    mode_override = req.mode_override or (req.mode.value if req.mode else "AUTO")
    filters = answer_service.filters_to_domain(req.filters.model_dump())
    phase = SECIPhase.COMBINATION
    if req.session_id:
        try:
            session = seci_service.get_session(req.session_id)
            phase = SECIPhase(session["phase"])
        except Exception:
            phase = SECIPhase.COMBINATION

    user_model = user_model_service.get_snapshot(req.user_id)
    first_decision = role_router_service.route(
        message=req.message,
        mode_override=mode_override,
        retrieval_signals={"retrieval_confidence": 0.0},
        user_model=user_model,
        session_phase=phase,
    )
    docs = retrieval_service.retrieve(
        collection_id=project["collection_id"],
        query=req.message,
        policy=first_decision.retrieval_policy,
        filters=filters,
    )
    retrieval_confidence = 0.0
    if docs:
        retrieval_confidence = max(float((d.metadata or {}).get("rerank_score", 0.0) or 0.0) for d in docs)
        retrieval_confidence = max(0.0, min(1.0, retrieval_confidence))

    decision = role_router_service.route(
        message=req.message,
        mode_override=mode_override,
        retrieval_signals={"retrieval_confidence": retrieval_confidence},
        user_model=user_model,
        session_phase=phase,
    )
    if decision.retrieval_policy != first_decision.retrieval_policy:
        docs = retrieval_service.retrieve(
            collection_id=project["collection_id"],
            query=req.message,
            policy=decision.retrieval_policy,
            filters=filters,
        )
        if docs:
            retrieval_confidence = max(float((d.metadata or {}).get("rerank_score", 0.0) or 0.0) for d in docs)
            retrieval_confidence = max(0.0, min(1.0, retrieval_confidence))
    citations = _citations_from_docs(docs)
    data, validation, citation_coverage = answer_service.build_answer(
        output_schema_id=decision.output_schema_id,
        message=req.message,
        citations=citations,
        strict_sources_only=bool(strict_citations),
    )
    completeness_score, missing_fields, insufficient_evidence = answer_service.assess_completeness(
        decision.output_schema_id, data
    )
    narrative_answer = ""
    if (not validation.schema_ok) or insufficient_evidence:
        narrative_answer = answer_service.build_narrative_answer(
            message=req.message,
            citations=citations,
            strict_sources_only=bool(strict_citations),
        )
    effective_policy = retrieval_service._merge_policy_and_filters(decision.retrieval_policy, filters)
    retrieval_service.log_retrieval(req.project_id, decision.mode_distance.value, req.message, filters, effective_policy)
    response = ChatResponse(
        mode=decision.mode_distance.value,
        data=data,
        narrative_answer=narrative_answer,
        citations=[
            CitationResponse(
                sid=c.sid,
                source=c.source,
                page=c.page,
                chunk_id=c.chunk_id,
                snippet=c.snippet,
                metadata=c.metadata,
            )
            for c in citations
        ],
        why_sources=answer_service.explain_sources(citations),
        retrieval={
            "k": int(effective_policy.get("k", filters.k)),
            "mmr": bool(effective_policy.get("mmr", filters.mmr)),
            "policy_applied": effective_policy,
            "filters": {
                "date_range_days": filters.date_range_days,
                "doctype": filters.doctype,
            },
            "retrieved_count": len(docs),
            "confidence": retrieval_confidence,
        },
        router=RouterInfoResponse(
            mode_distance=decision.mode_distance.value,
            seci_state=decision.seci_state,
            role_id=decision.role_id,
            confidence=decision.confidence,
            output_schema_id=decision.output_schema_id,
            retrieval_policy=RetrievalPolicyResponse(**decision.retrieval_policy),
            switch_suggestion=decision.switch_suggestion,
            clarification_questions=decision.clarification_questions or [],
            reason=decision.reason,
        ),
        validation=ValidationInfo(
            schema_ok=validation.schema_ok,
            errors=validation.errors,
            citation_coverage=citation_coverage,
            completeness_score=completeness_score,
            insufficient_evidence=insufficient_evidence,
            missing_fields=missing_fields,
        ),
        role=decision.role.value,
        routing_reason=decision.reason,
        routing_confidence=decision.confidence,
    )
    retrieval_service.log_chat_output(
        project_id=req.project_id,
        mode=decision.mode_distance.value,
        query=req.message,
        schema_ok=response.validation.schema_ok,
        response_json=json.dumps(response.data, ensure_ascii=False),
        citation_count=len(response.citations),
        confidence=float(response.retrieval.get("confidence", 0.0)),
        citation_coverage=citation_coverage,
    )
    latency_ms = int((time.perf_counter() - started) * 1000)
    retrieval_service.log_interaction(
        project_id=req.project_id,
        user_id=req.user_id,
        message=req.message,
        mode_override=mode_override,
        inferred_mode=decision.mode_distance.value,
        router_role=decision.role_id,
        seci_state=decision.seci_state.value,
        router_confidence=decision.confidence,
        strict_citations=bool(strict_citations),
        retrieval_k=int(effective_policy.get("k", filters.k)),
        citations_used=len(response.citations),
        latency_ms=latency_ms,
    )
    return response


@app.post("/v1/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    try:
        return _chat_impl(req)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/v1/onboarding", response_model=ChatResponse)
def onboarding(req: OnboardingRequest) -> ChatResponse:
    chat_req = ChatRequest(
        project_id=req.project_id,
        mode=req.mode,
        mode_override="SWP",
        message="Bring mich auf Stand: Entscheidungen, offene Fragen, ToDos, Risiken",
        filters=req.filters,
        strict_sources_only=req.strict_sources_only,
        strict_citations=req.strict_citations,
        user_id=req.user_id,
        session_id=req.session_id,
    )
    try:
        return _chat_impl(chat_req)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/v1/router/preview", response_model=RouterInfoResponse)
def router_preview(req: RouterPreviewRequest) -> RouterInfoResponse:
    phase = SECIPhase.COMBINATION
    if req.session_id:
        try:
            session = seci_service.get_session(req.session_id)
            phase = SECIPhase(session["phase"])
        except Exception:
            phase = SECIPhase.COMBINATION
    user_model = user_model_service.get_snapshot(req.user_id)
    decision = role_router_service.route(
        message=req.message,
        mode_override=req.mode_override,
        retrieval_signals={"retrieval_confidence": req.retrieval_confidence},
        user_model=user_model,
        session_phase=phase,
    )
    return RouterInfoResponse(
        mode_distance=decision.mode_distance.value,
        seci_state=decision.seci_state,
        role_id=decision.role_id,
        confidence=decision.confidence,
        output_schema_id=decision.output_schema_id,
        retrieval_policy=RetrievalPolicyResponse(**decision.retrieval_policy),
        switch_suggestion=decision.switch_suggestion,
        clarification_questions=decision.clarification_questions or [],
        reason=decision.reason,
    )


@app.post("/v1/seci/session/start")
def start_session(req: StartSessionRequest) -> dict:
    try:
        return seci_service.start_session(req.user_id, req.phase)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/v1/seci/session/{session_id}/event")
def apply_session_event(session_id: str, req: SessionEventRequest) -> dict:
    try:
        return seci_service.apply_event(
            session_id=session_id,
            event_type=req.event_type,
            target_phase=req.target_phase,
            target_state=req.target_state,
            reason=req.reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/v1/seci/session/{session_id}")
def get_session(session_id: str) -> dict:
    try:
        return seci_service.get_session(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/v1/learners/{user_id}/assessment")
def learner_assessment(user_id: str, req: AssessmentRequest) -> dict:
    return tutoring_service.run_assessment(
        user_id=user_id,
        topic=req.topic,
        score=req.score,
        confidence=req.confidence,
    )


@app.post("/v1/learners/{user_id}/practice")
def learner_practice(user_id: str, req: PracticeRequest) -> dict:
    return tutoring_service.run_practice(user_id=user_id, prompt=req.prompt, quality_score=req.quality_score)


@app.get("/v1/learners/{user_id}/schedule")
def learner_schedule(user_id: str) -> dict:
    return {"user_id": user_id, "schedule": user_model_service.get_schedule(user_id)}
