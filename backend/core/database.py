"""SQLite connection provider — shared, thread-safe, serialized writes."""
from __future__ import annotations

import contextlib
import sqlite3
import threading
from pathlib import Path
from typing import Any, Generator, Optional

from .config import DB_PATH

_write_lock = threading.RLock()


class Database:
    """Thread-local SQLite connection with serialized write transactions."""

    def __init__(self, path: Path = DB_PATH) -> None:
        self._path = path
        self._local = threading.local()

    def connect(self) -> sqlite3.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(self._path, timeout=30.0)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout = 30000")
            conn.execute("PRAGMA synchronous = NORMAL")
            self._local.conn = conn
        return conn

    @contextlib.contextmanager
    def write_transaction(self) -> Generator[sqlite3.Connection, None, None]:
        """Serialize database writes across threads with automatic commit/rollback."""
        with _write_lock:
            conn = self.connect()
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    def execute_write(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        with self.write_transaction() as conn:
            return conn.execute(sql, params)

    def setup(self, schema: str) -> None:
        with _write_lock:
            conn = self.connect()
            conn.executescript(schema)
            conn.commit()


db = Database()
