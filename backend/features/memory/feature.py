"""Memory feature — isolated; talks only through the event bus."""
from __future__ import annotations

from typing import Any, Dict, List

from ...core.base_feature import BaseFeature, register
from ...core.event_bus import Event


class MemoryPromptBuilder:
    """Compact recent-history block for the brain's system prompt."""

    MAX_TURNS = 10
    MAX_CHARS = 1200

    @classmethod
    def build(cls, turns: List[Dict[str, Any]]) -> str:
        if not turns:
            return ""
        lines = [
            f"{'User' if t['role'] == 'user' else 'HINATA'}: {t['content'][:180]}"
            for t in turns
        ]
        out = "Recent conversation:\n" + "\n".join(lines)
        return out[:cls.MAX_CHARS]


@register
class MemoryFeature(BaseFeature):
    name = "memory"

    def __init__(self) -> None:
        super().__init__()
        from .store import MemoryStore
        self.store = MemoryStore()

    def setup(self) -> None:
        self.store.setup()
        self.bus.subscribe("memory.append", self._on_append)
        self.bus.subscribe("memory.search.query", self._on_search)
        self.bus.subscribe("memory.recent.query", self._on_recent)

    def _on_append(self, event: Event) -> None:
        self.store.append(
            event.payload.get("role", "user"),
            event.payload.get("content", ""),
            event.payload.get("mood"),
        )

    def _on_search(self, event: Event) -> None:
        event.payload["results"] = self.store.search(
            event.payload.get("term", ""), event.payload.get("limit", 5),
        )

    def _on_recent(self, event: Event) -> None:
        event.payload["turns"] = self.store.recent(event.payload.get("limit", 20))

    def context_block(self) -> str:
        return MemoryPromptBuilder.build(self.store.recent(limit=12))

    def stats(self) -> Dict[str, Any]:
        return self.store.stats()
