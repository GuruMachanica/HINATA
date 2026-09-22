"""KnowledgeGraphStore — weighted triple store (reinforce, decay, query)."""
from __future__ import annotations

import time
from typing import Any, Dict, List

from ...core.database import db

_SCHEMA = """
CREATE TABLE IF NOT EXISTS entities (
    name TEXT PRIMARY KEY, kind TEXT DEFAULT 'concept',
    first_seen REAL, last_seen REAL, mention_count INTEGER DEFAULT 1
);
CREATE TABLE IF NOT EXISTS triples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject TEXT NOT NULL, relation TEXT NOT NULL, object TEXT NOT NULL,
    weight REAL DEFAULT 1.0, confidence REAL DEFAULT 0.5,
    source TEXT DEFAULT 'inferred', created_at REAL, last_reinforced REAL,
    UNIQUE(subject, relation, object)
);
CREATE INDEX IF NOT EXISTS idx_triples_subj ON triples(subject);
CREATE INDEX IF NOT EXISTS idx_triples_obj ON triples(object);
"""

DECAY_AFTER_S = 14 * 86400
DECAY_FACTOR = 0.92
MIN_WEIGHT = 0.05


class KnowledgeGraphStore:
    def setup(self) -> None:
        db.setup(_SCHEMA)

    def touch_entity(self, name: str, kind: str = "concept") -> None:
        now = time.time()
        db.connect().execute(
            "INSERT INTO entities(name, kind, first_seen, last_seen, mention_count) "
            "VALUES(?,?,?,?,1) ON CONFLICT(name) DO UPDATE SET "
            "last_seen=excluded.last_seen, mention_count=mention_count+1",
            (name[:80], kind, now, now),
        )
        db.connect().commit()

    def reinforce(self, subject: str, relation: str, object_: str,
                  confidence: float = 0.5, source: str = "inferred") -> None:
        now = time.time()
        db.connect().execute(
            "INSERT INTO triples(subject, relation, object, weight, confidence, source, "
            "created_at, last_reinforced) VALUES(?,?,?,1.0,?,?,?,?) "
            "ON CONFLICT(subject, relation, object) DO UPDATE SET "
            "weight=MIN(weight+0.5,20.0), last_reinforced=excluded.last_reinforced",
            (subject[:80], relation, object_[:120], confidence, source, now, now),
        )
        self.touch_entity(subject)
        self.touch_entity(object_)
        db.connect().commit()

    def decay(self) -> None:
        cutoff = time.time() - DECAY_AFTER_S
        db.connect().execute(
            "UPDATE triples SET weight=weight*? WHERE last_reinforced < ?",
            (DECAY_FACTOR, cutoff),
        )
        db.connect().execute("DELETE FROM triples WHERE weight < ?", (MIN_WEIGHT,))
        db.connect().commit()

    def related(self, entity: str, limit: int = 15) -> List[Dict[str, Any]]:
        rows = db.connect().execute(
            "SELECT subject, relation, object, weight, confidence, source FROM triples "
            "WHERE LOWER(subject)=? OR LOWER(object)=? ORDER BY weight DESC LIMIT ?",
            (entity.lower(), entity.lower(), limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def search(self, term: str, limit: int = 8) -> List[Dict[str, Any]]:
        like = f"%{term.lower()}%"
        rows = db.connect().execute(
            "SELECT subject, relation, object, weight, source FROM triples "
            "WHERE LOWER(subject) LIKE ? OR LOWER(object) LIKE ? ORDER BY weight DESC LIMIT ?",
            (like, like, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def stated_facts(self, limit: int = 10) -> List[Dict[str, Any]]:
        rows = db.connect().execute(
            "SELECT relation, object, weight, confidence FROM triples "
            "WHERE source='stated' ORDER BY weight DESC, last_reinforced DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    def summary(self) -> Dict[str, Any]:
        conn = db.connect()
        return {
            "entities": conn.execute("SELECT COUNT(*) c FROM entities").fetchone()["c"],
            "triples": conn.execute("SELECT COUNT(*) c FROM triples").fetchone()["c"],
            "explicit_facts": conn.execute(
                "SELECT COUNT(*) c FROM triples WHERE source='stated'"
            ).fetchone()["c"],
        }
