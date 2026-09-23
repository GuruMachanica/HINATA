"""Knowledge graph schema and tuning constants."""
from __future__ import annotations

KG_SCHEMA = """
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


def escape_like(term: str) -> str:
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def clamp_limit(value, default: int, cap: int = 100) -> int:
    try:
        return max(1, min(int(value or default), cap))
    except (TypeError, ValueError):
        return default
