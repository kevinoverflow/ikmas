import os
from typing import Any, Dict, List

import requests
import streamlit as st

API_BASE_URL = os.getenv("IKMAS_API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")

st.set_page_config(page_title="IKMAS", layout="wide")
st.title("IKMAS - Intelligent Knowledge Management Assistance System")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "project_id" not in st.session_state:
    st.session_state.project_id = None
if "last_sources" not in st.session_state:
    st.session_state.last_sources = []
if "last_why_sources" not in st.session_state:
    st.session_state.last_why_sources = []


def api_get(path: str, **kwargs):
    return requests.get(f"{API_BASE_URL}{path}", timeout=120, **kwargs)


def api_post(path: str, **kwargs):
    return requests.post(f"{API_BASE_URL}{path}", timeout=300, **kwargs)


def api_delete(path: str, **kwargs):
    return requests.delete(f"{API_BASE_URL}{path}", timeout=120, **kwargs)


def raise_with_detail(resp: requests.Response) -> None:
    if resp.ok:
        return
    try:
        detail = resp.json().get("detail", resp.text)
    except Exception:
        detail = resp.text
    raise RuntimeError(f"{resp.status_code} {resp.reason}. {detail}")


def fetch_projects() -> List[Dict[str, object]]:
    resp = api_get("/v1/projects")
    raise_with_detail(resp)
    return resp.json()


def selected_project_collection(projects: List[Dict[str, object]], project_id: str) -> str:
    match = next((p for p in projects if p["id"] == project_id), None)
    return match["collection_id"] if match else "default"


def _source_badges(source_ids: List[str]) -> str:
    if not source_ids:
        return "_no sources_"
    return " ".join(f"`{sid}`" for sid in source_ids)


def _render_swp(data: Dict[str, Any]) -> None:
    st.markdown("**TL;DR**")
    st.write(data.get("tldr", ""))

    st.markdown("**Decisions**")
    decisions = data.get("decisions", [])
    if decisions:
        for item in decisions:
            st.markdown(f"- **What:** {item.get('what', '')}")
            st.caption(f"Why: {item.get('why', '')} | Sources: {_source_badges(item.get('source_ids', []))}")
    else:
        st.caption("No decisions.")

    st.markdown("**Open Questions**")
    questions = data.get("open_questions", [])
    if questions:
        for item in questions:
            st.markdown(f"- {item.get('question', '')}")
            st.caption(f"Sources: {_source_badges(item.get('source_ids', []))}")
    else:
        st.caption("No open questions.")

    st.markdown("**Next Actions**")
    actions = data.get("next_actions", [])
    if actions:
        for item in actions:
            st.markdown(f"- {item.get('action', '')}")
            st.caption(
                f"Owner: {item.get('owner', '') or '-'} | Due: {item.get('due', '') or '-'} | "
                f"Sources: {_source_badges(item.get('source_ids', []))}"
            )
    else:
        st.caption("No actions.")

    st.markdown("**Risks**")
    risks = data.get("risks", [])
    if risks:
        for item in risks:
            st.markdown(f"- **Risk:** {item.get('risk', '')}")
            st.caption(
                f"Mitigation: {item.get('mitigation', '')} | Sources: {_source_badges(item.get('source_ids', []))}"
            )
    else:
        st.caption("No risks.")


def _render_esn(data: Dict[str, Any]) -> None:
    st.markdown("**Simple Explanation**")
    st.write(data.get("simple_explanation", ""))

    st.markdown("**Glossary**")
    glossary = data.get("glossary", [])
    if glossary:
        rows = [{"Term": item.get("term", ""), "Meaning": item.get("meaning", "")} for item in glossary]
        st.table(rows)
    else:
        st.caption("No glossary entries.")

    st.markdown("**Example From Sources**")
    ex = data.get("example_from_sources", {})
    st.write(ex.get("example", ""))
    st.caption(f"Sources: {_source_badges(ex.get('source_ids', []))}")

    st.markdown("**Common Pitfalls**")
    pitfalls = data.get("common_pitfalls", [])
    if pitfalls:
        for item in pitfalls:
            st.markdown(f"- {item}")
    else:
        st.caption("No common pitfalls.")


def _render_skm(data: Dict[str, Any]) -> None:
    st.markdown("**Patterns**")
    patterns = data.get("patterns", [])
    if patterns:
        for item in patterns:
            st.markdown(f"- {item.get('pattern', '')}")
            st.caption(f"Evidence: {_source_badges(item.get('evidence', []))}")
    else:
        st.caption("No patterns.")

    st.markdown("**Outliers**")
    outliers = data.get("outliers", [])
    if outliers:
        for item in outliers:
            st.markdown(f"- {item.get('outlier', '')}")
            st.caption(f"Evidence: {_source_badges(item.get('evidence', []))}")
    else:
        st.caption("No outliers.")

    st.markdown("**Hypotheses**")
    hypotheses = data.get("hypotheses", [])
    if hypotheses:
        for item in hypotheses:
            confidence = item.get("confidence", "medium")
            st.markdown(f"- {item.get('hypothesis', '')} (`{confidence}`)")
            st.caption(f"Evidence: {_source_badges(item.get('evidence', []))}")
    else:
        st.caption("No hypotheses.")


def render_structured_answer(bot: Dict[str, Any]) -> None:
    schema_id = (bot.get("router") or {}).get("output_schema_id")
    data = bot.get("data", {}) or {}
    if schema_id == "swp_v1":
        _render_swp(data)
    elif schema_id == "esn_v1":
        _render_esn(data)
    elif schema_id == "skm_v1":
        _render_skm(data)
    else:
        st.json(data)


left, center, right = st.columns([1, 2, 1])

with left:
    st.subheader("Workspace")
    st.caption(f"API: {API_BASE_URL}")
    try:
        health = api_get("/health")
        raise_with_detail(health)
        st.success("Backend erreichbar")
    except Exception as exc:
        st.error(f"Backend nicht erreichbar: {exc}")

    try:
        projects = fetch_projects()
    except Exception as exc:
        projects = []
        st.error(f"Projekte konnten nicht geladen werden: {exc}")

    if projects:
        labels = [f"{p['name']} ({p['collection_id']})" for p in projects]
        index = 0
        if st.session_state.project_id:
            for i, p in enumerate(projects):
                if p["id"] == st.session_state.project_id:
                    index = i
                    break
        selected = st.selectbox("Projekt", labels, index=index)
        selected_project = projects[labels.index(selected)]
        st.session_state.project_id = selected_project["id"]
    else:
        selected_project = None

    new_project_name = st.text_input("Neues Projekt")
    if st.button("Projekt anlegen", use_container_width=True) and new_project_name.strip():
        try:
            resp = api_post("/v1/projects", json={"name": new_project_name.strip()})
            raise_with_detail(resp)
            st.rerun()
        except Exception as exc:
            st.error(f"Fehler beim Anlegen: {exc}")

    st.divider()
    st.subheader("Modus & Filter")
    mode_override = st.selectbox("Modus", ["AUTO", "SWP", "ESN", "SKM"], index=0)
    strict_citations = st.checkbox("Strict: nur aus Quellen", value=True)
    k_value = st.slider("k", min_value=1, max_value=20, value=5)
    mmr_enabled = st.checkbox("MMR", value=False)
    date_range_days = st.number_input("Zeitraum (Tage)", min_value=0, max_value=3650, value=0)
    doctype_raw = st.text_input("Dokumenttypen (csv, optional)", value="")

    doctype = [x.strip() for x in doctype_raw.split(",") if x.strip()] or None
    active_filters = {
        "k": int(k_value),
        "mmr": bool(mmr_enabled),
        "date_range_days": int(date_range_days) if date_range_days else None,
        "doctype": doctype,
    }

    st.divider()
    st.subheader("File Hub")
    uploaded_files = st.file_uploader("PDF Upload", type=["pdf"], accept_multiple_files=True)
    conflict_mode = st.selectbox("Konfliktmodus", ["skip", "replace", "rename"], index=0)
    if st.button("Upload", type="primary", use_container_width=True):
        if not st.session_state.project_id:
            st.error("Bitte zuerst Projekt auswaehlen.")
        elif not uploaded_files:
            st.warning("Keine Dateien gewaehlt.")
        else:
            files_payload = [("files", (uf.name, uf.getvalue(), "application/pdf")) for uf in uploaded_files]
            try:
                resp = api_post(
                    "/v1/upload",
                    params={"project_id": st.session_state.project_id, "conflict_mode": conflict_mode},
                    files=files_payload,
                )
                raise_with_detail(resp)
                st.success(str(resp.json()["stats"]))
            except Exception as exc:
                st.error(f"Upload fehlgeschlagen: {exc}")

    if st.button("Reindex", use_container_width=True, disabled=not st.session_state.project_id):
        try:
            resp = api_post(
                "/v1/index/rebuild",
                json={"project_id": st.session_state.project_id, "reindex": True, "collection_id": "default"},
            )
            raise_with_detail(resp)
            st.success(f"Indexed {resp.json()['indexed_chunks']} chunks")
        except Exception as exc:
            st.error(f"Reindex fehlgeschlagen: {exc}")

with center:
    st.subheader("Chat")
    cta1, cta2 = st.columns(2)
    with cta1:
        if st.button("Onboarding", use_container_width=True, disabled=not st.session_state.project_id):
            try:
                payload = {
                    "project_id": st.session_state.project_id,
                    "mode": "SWP",
                    "filters": active_filters,
                    "strict_citations": strict_citations,
                }
                resp = api_post("/v1/onboarding", json=payload)
                raise_with_detail(resp)
                body = resp.json()
                st.session_state.chat_history.append({"user": "[Onboarding]", "bot": body})
                st.session_state.last_sources = body.get("citations", [])
                st.session_state.last_why_sources = body.get("why_sources", [])
            except Exception as exc:
                st.error(f"Onboarding fehlgeschlagen: {exc}")
    with cta2:
        st.button("Interview (coming soon)", disabled=True, use_container_width=True)

    user_query = st.chat_input("Frage zum Projektwissen...")
    if user_query and st.session_state.project_id:
        try:
            payload = {
                "project_id": st.session_state.project_id,
                "message": user_query,
                "mode_override": mode_override,
                "filters": active_filters,
                "strict_citations": strict_citations,
                "user_id": "streamlit-user",
            }
            resp = api_post("/v1/chat", json=payload)
            raise_with_detail(resp)
            body = resp.json()
            st.session_state.chat_history.append({"user": user_query, "bot": body})
            st.session_state.last_sources = body.get("citations", [])
            st.session_state.last_why_sources = body.get("why_sources", [])
        except Exception as exc:
            st.error(f"Chat-Fehler: {exc}")

    for turn in st.session_state.chat_history:
        st.chat_message("user").markdown(turn["user"])
        bot = turn["bot"]
        with st.chat_message("assistant"):
            narrative_answer = (bot.get("narrative_answer") or "").strip()
            if narrative_answer:
                st.markdown("**LLM Summary**")
                st.write(narrative_answer)
                st.divider()
            render_structured_answer(bot)
            with st.expander("Raw JSON", expanded=False):
                st.json(bot.get("data", {}))
        router = bot.get("router", {})
        validation = bot.get("validation", {})
        st.caption(
            f"Mode={bot.get('mode')} | Role={router.get('role_id', bot.get('role', ''))} | "
            f"schema_ok={validation.get('schema_ok', False)} | citation_coverage={validation.get('citation_coverage', 0.0):.2f} | "
            f"completeness={validation.get('completeness_score', 0.0):.2f}"
        )
        if validation.get("insufficient_evidence", False):
            missing = validation.get("missing_fields", [])
            if missing:
                st.warning(f"Unvollstaendige Evidenz fuer Felder: {', '.join(missing)}")
            else:
                st.warning("Unvollstaendige Evidenz fuer strukturierte Antwort.")
        suggestion = router.get("switch_suggestion")
        if suggestion:
            st.info(suggestion)
        clarifications = router.get("clarification_questions", [])
        if clarifications:
            st.markdown("**Rueckfragen zur Moduswahl**")
            for q in clarifications:
                st.write(f"- {q}")

with right:
    st.subheader("Quellenpanel")
    if not st.session_state.last_sources:
        st.info("Noch keine Quellen fuer diese Sitzung.")
    else:
        for citation in st.session_state.last_sources:
            st.markdown(
                f"**[{citation['sid']}]** {citation['source']} - Seite {citation.get('page', 'N/A')}"
            )
            st.caption(citation.get("snippet", ""))

    st.divider()
    st.markdown("**Warum diese Quellen?**")
    if st.session_state.last_why_sources:
        for reason in st.session_state.last_why_sources:
            st.write(f"- {reason}")
    else:
        st.caption("Keine Begruendung verfuegbar.")

    st.divider()
    st.markdown("**Aehnliche Stellen (optional)**")
    st.caption("Wird in MVP+ ueber semantic linking erweitert.")

    st.divider()
    st.subheader("Dokumente")
    if st.session_state.project_id:
        try:
            docs_resp = api_get("/v1/documents", params={"project_id": st.session_state.project_id})
            raise_with_detail(docs_resp)
            docs = docs_resp.json().get("documents", [])
        except Exception as exc:
            docs = []
            st.error(f"Dokumentliste fehlgeschlagen: {exc}")
    else:
        docs = []

    if not docs:
        st.caption("Keine Dokumente im Projekt.")
    else:
        project_collection = selected_project_collection(projects if "projects" in locals() else [], st.session_state.project_id)
        for doc in docs:
            st.markdown(f"- `{doc['filename']}` ({doc['status']}, chunks={doc['chunk_count']})")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Download", key=f"dl::{doc['id']}", use_container_width=True):
                    try:
                        dl = api_get(
                            f"/v1/files/{doc['filename']}/download",
                            params={"collection_id": project_collection},
                        )
                        raise_with_detail(dl)
                        st.download_button(
                            "Datei speichern",
                            data=dl.content,
                            file_name=doc["filename"],
                            mime="application/pdf",
                            key=f"save::{doc['id']}",
                            use_container_width=True,
                        )
                    except Exception as exc:
                        st.error(f"Download fehlgeschlagen: {exc}")
            with c2:
                if st.button("Delete", key=f"del::{doc['id']}", use_container_width=True):
                    try:
                        dr = api_delete(f"/v1/documents/{doc['id']}")
                        raise_with_detail(dr)
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Loeschen fehlgeschlagen: {exc}")
