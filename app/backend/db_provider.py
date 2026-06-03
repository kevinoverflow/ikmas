from __future__ import annotations

from typing import Callable

from app.backend.sqlite_store import create_session, get_conn, init_db, log_turn, save_artefacts
from app.domain.types import TurnRecord


class DBProvider:
    def __init__(
        self,
        *,
        init_db_fn: Callable[[], None] = init_db,
        get_conn_fn: Callable = get_conn,
        create_session_fn: Callable[[str], None] = create_session,
        log_turn_fn: Callable[[TurnRecord], None] = log_turn,
        save_artefacts_fn: Callable[[list[dict], str, list[dict]], list[int]] = save_artefacts,
    ):
        self._init_db = init_db_fn
        self._get_conn = get_conn_fn
        self._create_session = create_session_fn
        self._log_turn = log_turn_fn
        self._save_artefacts = save_artefacts_fn
        self._initialized = False

    def init(self) -> None:
        if not self._initialized:
            self._init_db()
            self._initialized = True

    def connect(self):
        return self._get_conn()

    def create_session(self, session_id: str) -> None:
        self.init()
        self._create_session(session_id)

    def log_turn(self, turn: TurnRecord) -> None:
        self.init()
        self._log_turn(turn)

    def save_artefacts(self, artefacts: list[dict], project: str, refs: list[dict]) -> list[int]:
        self.init()
        return self._save_artefacts(artefacts, project, refs)
