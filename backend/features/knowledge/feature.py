"""Knowledge feature — isolated KG service; bus-driven."""
from __future__ import annotations

from typing import Any, List, Optional

from ...core.base_feature import BaseFeature, register
from ...core.event_bus import Event
from .extractor import extract_entities, extract_facts
from .graph_store import KnowledgeGraphStore


@register
class KnowledgeFeature(BaseFeature):
    name = "knowledge"

    def __init__(self) -> None:
        super().__init__()
        self.store = KnowledgeGraphStore()

    def setup(self) -> None:
        self.store.setup()
        self.bus.subscribe("knowledge.search", self._on_search)
        self.bus.subscribe("knowledge.fact", self._on_fact)
        self.bus.subscribe("knowledge.context", self._on_context)
        self.bus.subscribe("knowledge.observe", self._on_observe)

    # -- bus handlers ---------------------------------------------------------
    def _on_search(self, event: Event) -> None:
        event.payload["results"] = self.store.search(
            event.payload.get("term", ""), event.payload.get("limit", 8),
        )

    def _on_fact(self, event: Event) -> None:
        self.store.reinforce(
            "user", event.payload.get("relation", "fact"),
            event.payload.get("object", ""), event.payload.get("confidence", 0.9),
            source="stated",
        )
        self.store.touch_entity(event.payload.get("object", ""))

    def _on_context(self, event: Event) -> None:
        event.payload["block"] = self.context_block(event.payload.get("hints"))

    def _on_observe(self, event: Event) -> None:
        self.observe_turn(
            event.payload.get("user_text", ""), event.payload.get("reply", ""),
        )

    # -- turn ingestion (called by brain via bus) ------------------------------
    def observe_turn(self, user_text: str, hinata_reply: str) -> Dict[str, Any]:
        entities = extract_entities(user_text)
        for ent in entities:
            self.store.touch_entity(ent)
            self.store.reinforce("user", "talks_about", ent, confidence=0.5)
        for i in range(len(entities)):
            for j in range(i + 1, len(entities)):
                self.store.reinforce(entities[i], "co_occurs", entities[j], confidence=0.35)
        facts = extract_facts(user_text)
        for relation, obj, conf in facts:
            self.store.reinforce("user", relation, obj, confidence=conf, source="stated")
        for ent in extract_entities(hinata_reply):
            self.store.touch_entity(ent, kind="topic")
        self.store.decay()
        self.bus.connect if hasattr(self.bus, "connect") else None
        return {"entities": entities, "facts_added": [
            {"relation": r, "object": o, "confidence": c} for r, o, c in facts
        ]}

    # -- prompt context --------------------------------------------------------
    def context_block(self, entity_hints: Optional[List[str]] = None, max_chars: int = 700) -> str:
        parts: List[str] = []
        facts = self.store.stated_facts(limit=10)
        if facts:
            parts.append("Known facts about the user:\n" + "\n".join(
                f"- user {f['relation']}: {f['object']}" for f in facts))
        lines: List[str] = []
        for ent in (entity_hints or [])[:6]:
            for edge in self.store.related(ent, limit=6):
                if edge["source"] != "stated":
                    lines.append(f"- {edge['subject']} --[{edge['relation']}]--> "
                                 f"{edge['object']} (weight {edge['weight']:.1f})")
        if lines:
            parts.append("Knowledge graph associations:\n" + "\n".join(lines[:12]))
        out = "\n\n".join(parts)
        return out[:max_chars]

    def summary(self) -> Dict[str, Any]:
        return self.store.summary()
