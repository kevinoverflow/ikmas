from pathlib import Path
import sys

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.backend.user_scope import user_workspace_id
from app.ui.artifacts import render_artifact_browser
from app.ui.auth import logout, render_auth_workflow
from app.ui.chat import render_chat
from app.ui.constants import LOGICAL_COLLECTION_ID
from app.ui.files import render_file_workspace
from app.ui.sidebar import render_sidebar
from app.ui.state import init_session_state

ABOUT_TEXT = """
# IKMAS - Intelligent Knowledge Management Assistance System

IKMAS is a research prototype for context-sensitive knowledge management support using Generative AI. The system combines Large Language Models (LLMs), Retrieval-Augmented Generation (RAG), vector-based retrieval, and role-specific AI agents to support knowledge-intensive processes such as documentation, semantic linking, contextual reconstruction, learning support, and knowledge reuse.

## Core Features

- Upload and processing of organizational knowledge artifacts
  (PDF, DOCX, PPTX, scanned documents)
- OCR-based extraction of text from images and scanned files
- Retrieval-Augmented Generation (RAG)
- Semantic document retrieval using vector embeddings
- Theory-driven routing of role-specific GenAI agents
- Support for knowledge creation, reuse, contextualization, and transfer

## AI Infrastructure

IKMAS uses Large Language Models provided through the SCADS.AI infrastructure at TU Dresden. Model access is implemented through OpenAI-compatible interfaces, enabling flexible integration of different foundation models.

## Technology Stack

### LLM & Agent Framework
- OpenAI Python SDK
- LangChain
- LangChain Core
- LangChain Community
- LangChain OpenAI
- LangChain Text Splitters
- Transformers
- Tiktoken
- LangSmith

### Knowledge Retrieval & Storage
- ChromaDB

### Document Processing
- PyPDF
- PyMuPDF
- python-docx
- python-pptx

### OCR & Computer Vision
- Tesseract OCR
- pytesseract
- OpenCV

### Application Framework
- Streamlit
- Authlib

### Development & Testing
- Pytest

## Research Context

IKMAS is being developed as part of ongoing research at TU Dresden on the integration of Generative AI into organizational knowledge management processes.

The prototype operationalizes concepts from:

- SECI Knowledge Conversion (Nonaka & Takeuchi, 1995)
- Knowledge Reuse Theory (Markus, 2001)

through routed LLM agents and knowledge-artifact-centered workflows.

## Open Source Software

This application incorporates open-source software packages that remain subject to their respective licenses. Please consult the respective projects for licensing information.

## Repository

https://git.codip.tu-dresden.de/kevin.hoang/ikmas

## License

Copyright (c) 2026 Kevin Hoang

IKMAS is licensed under the Apache License, Version 2.0.

You may obtain a copy of the License at:

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.

See the [LICENSE](LICENSE) file for the full license text.

Third-party software components remain subject to their respective licenses.
"""


def main() -> None:
    st.set_page_config(
        page_title="IKMAS",
        layout="wide",
        menu_items={
            "About": ABOUT_TEXT,
        },
    )

    st.title("Intelligent Knowledge Management Assistance System")

    init_session_state(st.session_state)

    if not render_auth_workflow():
        st.stop()

    current_user = st.session_state.auth_user
    if current_user is None:
        st.stop()

    collection_id = user_workspace_id(
        current_user["id"],
        LOGICAL_COLLECTION_ID,
    )

    render_sidebar(current_user, on_logout=logout)

    main_col, artifact_col = st.columns(
        [0.68, 0.32],
        gap="large",
    )

    with main_col:
        render_file_workspace(collection_id)
        render_chat(current_user, collection_id)

    with artifact_col:
        render_artifact_browser(
            collection_id,
            st.session_state.chat_history,
        )


if __name__ == "__main__":
    main()