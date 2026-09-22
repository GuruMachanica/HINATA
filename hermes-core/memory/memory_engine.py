"""
HINATA Multi-Tier Memory Engine
Stores and retrieves episodic, semantic, relationship, and procedural records.
Fault-tolerant JSON file persistence. Strictly under 100 LOC.
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Any

class MemoryEngine:
    TIERS = ["episodic", "semantic", "relationship", "procedural"]

    def __init__(self, storage_dir: Path):
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.data: Dict[str, List[Dict[str, Any]]] = {}
        self._load_all()

    def _file_for(self, tier: str) -> Path:
        return self.storage_dir / f"{tier}.json"

    def _load_all(self):
        for tier in self.TIERS:
            p = self._file_for(tier)
            if p.exists():
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        self.data[tier] = json.load(f)
                except Exception:
                    self.data[tier] = []
            else:
                self.data[tier] = []

    def remember(self, tier: str, key: str, content: str, meta: Dict = None) -> None:
        """Appends a new entry to the designated memory tier."""
        if tier not in self.TIERS:
            raise ValueError(f"Invalid tier: {tier}")
        entry = {
            "key": key,
            "content": content,
            "timestamp": time.time(),
            "meta": meta or {}
        }
        self.data[tier].append(entry)
        try:
            with open(self._file_for(tier), "w", encoding="utf-8") as f:
                json.dump(self.data[tier], f, indent=2)
        except Exception:
            pass  # Fault isolation

    def recall(self, tier: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Returns the most recent memories for a tier."""
        return self.data.get(tier, [])[-limit:]
