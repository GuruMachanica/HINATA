"""KnowledgeGraphStore — weighted triple store (reinforce, decay, query)."""
from __future__ import annotations

import time
from typing import Any, Dict, List

from ...core.database import db
from .kg_schema import KG_SCHEMA, DECAY_AFTER_S, DECAY_FACTOR, MIN_WEIGHT, escape_like, clamp_limit


class KnowledgeGraphStore:
    def setup(self) -> None:
        db.setup(KG_SCHEMA)

    def touch_entity(self, name: str, kind: str = "concept") -> None:
        now = time.time()
        with db.write_transaction() as conn:
            conn.execute(
                "INSERT INTO entities(name, kind, first_seen, last_seen, mention_count) "
                "VALUES(?,?,?,?,1) ON CONFLICT(name) DO UPDATE SET "
                "last_seen=excluded.last_seen, mention_count=mention_count+1",
                (name[:80], kind, now, now),
            )

    def reinforce(self, subject: str, relation: str, object_: str,
                  confidence: float = 0.5, source: str = "inferred") -> None:
        now = time.time()
        with db.write_transaction() as conn:
            conn.execute(
                "INSERT INTO triples(subject, relation, object, weight, confidence, source, "
                "created_at, last_reinforced) VALUES(?,?,?,1.0,?,?,?,?) "
                "ON CONFLICT(subject, relation, object) DO UPDATE SET "
                "weight=MIN(weight+0.5,20.0), last_reinforced=excluded.last_reinforced",
                (subject[:80], relation, object_[:120], confidence, source, now, now),
            )
            # update entities within same transaction
            conn.execute(
                "INSERT INTO entities(name, kind, first_seen, last_seen, mention_count) "
                "VALUES(?, 'concept', ?, ?, 1) ON CONFLICT(name) DO UPDATE SET "
                "last_seen=excluded.last_seen, mention_count=mention_count+1",
                (subject[:80], now, now),
            )
            conn.execute(
                "INSERT INTO entities(name, kind, first_seen, last_seen, mention_count) "
                "VALUES(?, 'concept', ?, ?, 1) ON CONFLICT(name) DO UPDATE SET "
                "last_seen=excluded.last_seen, mention_count=mention_count+1",
                (object_[:80], now, now),
            )

    def decay(self) -> None:
        cutoff = time.time() - DECAY_AFTER_S
        with db.write_transaction() as conn:
            conn.execute(
                "UPDATE triples SET weight=weight*? WHERE last_reinforced < ?",
                (DECAY_FACTOR, cutoff),
            )
            conn.execute("DELETE FROM triples WHERE weight < ?", (MIN_WEIGHT,))

    def related(self, entity: str, limit: int = 15) -> List[Dict[str, Any]]:
        target = entity.strip().lower()
        rows = db.connect().execute(
            "SELECT subject, relation, object, weight, confidence, source FROM triples "
            "WHERE LOWER(subject)=? OR LOWER(object)=? ORDER BY weight DESC LIMIT ?",
            (target, target, clamp_limit(limit, 15)),
        ).fetchall()
        return [dict(r) for r in rows]

    def search(self, term: str, limit: int = 8) -> List[Dict[str, Any]]:
        like = f"%{escape_like(term.strip().lower())}%"
        rows = db.connect().execute(
            "SELECT subject, relation, object, weight, source FROM triples "
            "WHERE (LOWER(subject) LIKE ? ESCAPE '\\' OR LOWER(object) LIKE ? ESCAPE '\\') "
            "ORDER BY weight DESC LIMIT ?",
            (like, like, clamp_limit(limit, 8)),
        ).fetchall()
        return [dict(r) for r in rows]

    def stated_facts(self, limit: int = 10) -> List[Dict[str, Any]]:
        rows = db.connect().execute(
            "SELECT relation, object, weight, confidence FROM triples "
            "WHERE source='stated' ORDER BY weight DESC, last_reinforced DESC LIMIT ?",
            (clamp_limit(limit, 10),),
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

    def clear(self, entity: str | None = None) -> int:
        with db.write_transaction() as conn:
            if entity and entity.strip().lower() not in ("all", "everything"):
                target = entity.lower().strip()
                # Exact match deletion to prevent wiping unrelated entities/triples
                c1 = conn.execute(
                    "DELETE FROM triples WHERE LOWER(subject) = ? OR LOWER(object) = ?",
                    (target, target),
                ).rowcount
                c2 = conn.execute(
                    "DELETE FROM entities WHERE LOWER(name) = ?",
                    (target,),
                ).rowcount
                return c1 + c2
            else:
                c1 = conn.execute("DELETE FROM triples").rowcount
                c2 = conn.execute("DELETE FROM entities").rowcount
                return c1 + c2
