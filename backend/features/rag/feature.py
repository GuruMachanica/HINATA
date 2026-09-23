"""RAGFeature — semantic memory retrieval wired over the event bus.

Indexes every stored message as a vector; the brain queries
`rag.search` for "what did we say about X" style recall.
"""
from __future__ import annotations

import logging

from ...core.base_feature import BaseFeature, register
from .vector_store import VectorStore

log = logging.getLogger("hinata.rag")


@register
class RAGFeature(BaseFeature):
    name = "rag"

    def __init__(self) -> None:
        super().__init__()
        self.store = VectorStore()

    def setup(self) -> None:
        self.store.setup()
        self.bus.subscribe("memory.stored", self._on_stored)
        self.bus.subscribe("rag.search", self._on_search)
        if self.store.available:
            log.info("RAG online (nomic-embed-text)")
        else:
            log.warning("RAG offline — embedding endpoint unreachable")

    def _on_stored(self, event) -> None:
        message_id = event.payload.get("message_id")
        content = event.payload.get("content") or ""
        if message_id and content.strip():
            try:
                self.store.index_message(int(message_id), content)
            except Exception as exc:
                log.warning("index failed for msg %s: %s", message_id, exc)

    def _on_search(self, event):
        query = event.payload.get("query") or ""
        limit = int(event.payload.get("limit") or 6)
        try:
            hits = self.store.search(query, limit)
            event.reply({"hits": hits})
        except Exception as exc:
            log.warning("rag.search failed: %s", exc)
            event.reply({"hits": []})

    def search(self, query: str, limit: int = 6) -> list:
        try:
            return self.store.search(query, limit)
        except Exception:
            return []
