"""Memory + Knowledge-Graph tools — lets the brain query what she knows."""
from __future__ import annotations

from typing import Any

from ..base import Tool, ToolParam, ToolResult, ToolRiskLevel
from ....core.event_bus import Event


class RecallMemoryTool(Tool):
    name = "recall_memory"
    description = "Search past conversations by keyword. Use when the user references something earlier."
    risk_level = ToolRiskLevel.READ_ONLY
    params = [
        ToolParam("term", "string", "keyword to search in conversation history", required=True, min_len=1, max_len=100),
    ]

    def run(self, term: str = "", **_: Any) -> ToolResult:
        event = Event(name="memory.search", payload={"term": term, "limit": 5}, source=self.name)
        results = self._ask_bus(event)
        if not results:
            return ToolResult(ok=True, output=f"no past conversation matches '{term}'")
        lines = [f"[{r['role']}] {r['content'][:120]}" for r in results]
        return ToolResult(ok=True, output="\n".join(lines), data={"results": results})

    @staticmethod
    def _ask_bus(event: Event) -> list | None:
        from ....core.event_bus import bus
        response = bus.emit("memory.search.query", dict(event.payload), source=event.source)
        return response.payload.get("results")


class KnowledgeQueryTool(Tool):
    name = "query_knowledge"
    description = "Search the knowledge graph for facts and associations about a person/topic/thing."
    risk_level = ToolRiskLevel.READ_ONLY
    params = [
        ToolParam("term", "string", "entity or topic to query", required=True, min_len=1, max_len=100),
    ]

    def run(self, term: str = "", **_: Any) -> ToolResult:
        from ....core.event_bus import bus
        response = bus.emit("knowledge.search", {"term": term, "limit": 8}, source=self.name)
        edges = response.payload.get("results") or []
        if not edges:
            return ToolResult(ok=True, output=f"nothing in the knowledge graph about '{term}'")
        lines = [f"{e['subject']} --[{e['relation']}]--> {e['object']} (w={e['weight']:.1f})" for e in edges]
        return ToolResult(ok=True, output="\n".join(lines), data={"edges": edges})


class RememberFactTool(Tool):
    name = "remember_fact"
    description = "Store an explicit fact about the user permanently in the knowledge graph."
    risk_level = ToolRiskLevel.MUTATING
    params = [
        ToolParam("relation", "string", "relation type e.g. likes, is_a, has_value", required=True, min_len=1, max_len=50),
        ToolParam("object", "string", "the fact content or entity", required=True, min_len=1, max_len=150),
    ]

    def run(self, relation: str = "", object: str = "", **_: Any) -> ToolResult:
        from ....core.event_bus import bus
        bus.emit("knowledge.fact", {"relation": relation, "object": object, "confidence": 0.95},
                 source=self.name)
        return ToolResult(ok=True, output=f"remembered: user {relation} {object}")


class ResetKnowledgeTool(Tool):
    name = "reset_knowledge"
    description = (
        "Delete or reset facts in the knowledge base or memory. "
        "Use target='all' to purge all knowledge and past conversation history, "
        "or pass a specific keyword/topic to delete only matching entries."
    )
    risk_level = ToolRiskLevel.MUTATING
    params = [
        ToolParam("target", "string", "'all' or specific entity/topic name", required=False, min_len=1, max_len=100),
    ]

    def run(self, target: str = "all", **_: Any) -> ToolResult:
        from ....core.event_bus import bus
        clean_target = (target or "all").strip().lower()
        resp_kg = bus.emit("knowledge.clear", {"entity": clean_target}, source=self.name)
        kg_cleared = resp_kg.payload.get("cleared_count", 0)

        mem_cleared = 0
        if clean_target in ("all", "memory", "everything", "history"):
            resp_mem = bus.emit("memory.clear", {}, source=self.name)
            mem_cleared = resp_mem.payload.get("cleared_count", 0)

        return ToolResult(
            ok=True,
            output=f"Knowledge base reset successfully. Cleared {kg_cleared} knowledge items and {mem_cleared} conversation turns.",
            data={"kg_cleared": kg_cleared, "memory_cleared": mem_cleared},
        )
