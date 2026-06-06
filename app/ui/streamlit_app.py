from pathlib import Path
import sys

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.backend.user_scope import user_workspace_id
from app.ui.auth import logout, render_auth_workflow
from app.ui.chat import render_chat
from app.ui.constants import LOGICAL_COLLECTION_ID
from app.ui.files import render_file_workspace
from app.ui.sidebar import render_sidebar
from app.ui.state import init_session_state


def main() -> None:
    st.set_page_config(page_title="IKMAS", layout="centered")
    st.title("Intelligent Knowledge Management Assistance System")

    init_session_state(st.session_state)
    if not render_auth_workflow():
        st.stop()

    current_user = st.session_state.auth_user
    if current_user is None:
        st.stop()

    collection_id = user_workspace_id(current_user["id"], LOGICAL_COLLECTION_ID)

    render_sidebar(current_user, on_logout=logout)
    render_file_workspace(collection_id)
    render_chat(current_user, collection_id)


main()
