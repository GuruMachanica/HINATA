"""VectorStore — embedding-based semantic retrieval (RAG) over SQLite.

Stores message embeddings as BLOBs and recalls by cosine similarity.
Uses Ollama's nomic-embed-text (274 MB, fully local) for vectors.
"""
from __future__ import annotations

import json
import struct
import time
import urllib.request
from typing import Dict, List, Optional, Tuple

from ...core.config import model_endpoint
from ...core.database import db

EMBED_MODEL = "nomic-embed-text"
def _embed_url() -> str:
    return model_endpoint().replace("/v1", "") + "/api/embeddings"
_TOP_K = 6
_MIN_SIM = 0.35

_SCHEMA = """
CREATE TABLE IF NOT EXISTS embeddings (
    message_id INTEGER PRIMARY KEY REFERENCES messages(id) ON DELETE CASCADE,
    vector BLOB NOT NULL,
    created_at REAL NOT NULL
);
"""


def pack(vec: List[float]) -> bytes:
    return struct.pack(f"{len(vec)}f", *vec)


def unpack(blob: bytes) -> List[float]:
    return list(struct.unpack(f"{len(blob)//4}f", blob))


def cosine(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(x * x for x in b) ** 0.5
    return dot / (na * nb) if na and nb else 0.0


class VectorStore:
    def __init__(self) -> None:
        self._available: Optional[bool] = None

    def setup(self) -> None:
        db.setup(_SCHEMA)

    def _embed(self, text: str) -> Optional[List[float]]:
        body = json.dumps({"model": EMBED_MODEL, "prompt": text[:800]}).encode()
        req = urllib.request.Request(
            _embed_url(), data=body, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode())["embedding"]
        except Exception:
            return None

    @property
    def available(self) -> bool:
        if self._available is None:
            self._available = self._embed("ping") is not None
        return self._available

    def index_message(self, message_id: int, content: str) -> bool:
        vec = self._embed(content)
        if vec is None:
            return False
        with db.write_transaction() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO embeddings(message_id, vector, created_at) VALUES(?,?,?)",
                (message_id, pack(vec), time.time()),
            )
        return True

    def search(self, query: str, limit: int = _TOP_K) -> List[Dict[str, float]]:
        """Top-N semantically similar past messages: [{content, role, score}]."""
        qvec = self._embed(query)
        if qvec is None:
            return []
        rows = db.connect().execute(
            "SELECT m.role, m.content, e.vector FROM embeddings e "
            "JOIN messages m ON m.id = e.message_id ORDER BY e.created_at DESC LIMIT 800"
        ).fetchall()
        scored: List[Tuple[float, Dict[str, float]]] = []
        for r in rows:
            score = cosine(qvec, unpack(r["vector"]))
            if score >= _MIN_SIM:
                scored.append((score, {"content": r["content"], "role": r["role"], "score": round(score, 3)}))
        scored.sort(key=lambda t: -t[0])
        return [item for _, item in scored[:max(1, min(limit, 12))]]
