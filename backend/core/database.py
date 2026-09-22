"""SQLite connection provider — shared, thread-safe, feature-scoped tables."""
from __future__ import annotations

import sqlite3
import threading
from pathlib import Path
from typing import Optional

from .config import DB_PATH

_lock = threading.Lock()
_conn: Optional[sqlite3.Connection] = None


class Database:
    """One shared SQLite connection; each feature owns its own tables."""

    def __init__(self, path: Path = DB_PATH) -> None:
        self._path = path
        self._local = threading.local()

    def connect(self) -> sqlite3.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(self._path)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn = conn
        return conn

    def setup(self, schema: str) -> None:
        with _lock:
            self.connect().executescript(schema)
            self.connect().commit()


db = Database()
