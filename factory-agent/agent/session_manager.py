from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4


class Session:
    def __init__(self) -> None:
        self.session_id: str = str(uuid4())[:8]
        self.created_at: datetime = datetime.now()
        self.history: list[dict[str, Any]] = []

    def add_entry(self, entry: dict[str, Any]) -> None:
        self.history.append(entry)

    def last_query(self) -> str | None:
        if self.history:
            return self.history[-1].get("query")
        return None


class SessionManager:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    def create_session(self) -> Session:
        session = Session()
        self._sessions[session.session_id] = session
        return session

    def get_session(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)

    def get_or_create(self, session_id: str | None = None) -> Session:
        if session_id and session_id in self._sessions:
            return self._sessions[session_id]
        return self.create_session()
