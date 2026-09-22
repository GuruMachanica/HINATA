"""MemoryStore — persistent conversation history (sessions auto-rotate)."""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from ...core.database import db

_SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('user','assistant','system')),
    content TEXT NOT NULL,
    mood TEXT,
    created_at REAL
);
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
"""

SESSION_TIMEOUT_S = 2 * 3600


def _escape_like(term: str) -> str:
    """Escape SQL LIKE wildcards (% and _) for literal substring matching."""
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class MemoryStore:
    def __init__(self) -> None:
        self._session: Optional[str] = None

    def setup(self) -> None:
        db.setup(_SCHEMA)

    def session_id(self) -> str:
        if self._session:
            return self._session
        row = db.connect().execute(
            "SELECT session_id, created_at FROM messages ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if row and (time.time() - row["created_at"]) < SESSION_TIMEOUT_S:
            self._session = row["session_id"]
        else:
            self._session = f"s{int(time.time())}"
        return self._session

    def append(self, role: str, content: str, mood: str | None = None) -> int:
        with db.write_transaction() as conn:
            cur = conn.execute(
                "INSERT INTO messages(session_id, role, content, mood, created_at) VALUES(?,?,?,?,?)",
                (self.session_id(), role, content, mood, time.time()),
            )
            return cur.lastrowid

    def recent(self, limit: int = 20) -> List[Dict[str, Any]]:
        safe_limit = max(1, min(int(limit or 20), 100))
        rows = db.connect().execute(
            "SELECT role, content, mood, created_at FROM messages ORDER BY id DESC LIMIT ?",
            (safe_limit,),
        ).fetchall()
        return [dict(r) for r in reversed(rows)]

    def search(self, term: str, limit: int = 5) -> List[Dict[str, Any]]:
        safe_limit = max(1, min(int(limit or 5), 50))
        pattern = f"%{_escape_like(term)}%"
        rows = db.connect().execute(
            "SELECT role, content, created_at FROM messages WHERE content LIKE ? ESCAPE '\\' "
            "ORDER BY created_at DESC LIMIT ?",
            (pattern, safe_limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def stats(self) -> Dict[str, Any]:
        conn = db.connect()
        total = conn.execute("SELECT COUNT(*) c FROM messages").fetchone()["c"]
        sessions = conn.execute("SELECT COUNT(DISTINCT session_id) c FROM messages").fetchone()["c"]
        return {"total_messages": total, "sessions": sessions}

    def clear(self) -> int:
        with db.write_transaction() as conn:
            c = conn.execute("DELETE FROM messages").rowcount
            return c
