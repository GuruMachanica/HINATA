"""RAG tools — semantic recall over everything ever said."""
from __future__ import annotations

import logging
from typing import Any

from ..base import Tool, ToolParam, ToolResult, ToolRiskLevel

log = logging.getLogger("hinata.tools.rag")


class SemanticSearchTool(Tool):
    name = "semantic_search"
    description = (
        "Search the meaning of every past conversation, not just keywords. Use when "
        "the user asks 'what did we talk about', 'have I told you about', or when "
        "past context would help but exact words are unknown."
    )
    risk_level = ToolRiskLevel.READ_ONLY
    params = [
        ToolParam("query", "string", "what to recall semantically", required=True,
                  min_len=2, max_len=300),
        ToolParam("limit", "integer", "max results (1-8)", required=False,
                  min_val=1, max_val=8),
    ]

    def run(self, query: str = "", limit: int = 5, **_: Any) -> ToolResult:
        if not query.strip():
            return ToolResult(ok=False, output="empty query")
        try:
            from ....features.rag.vector_store import VectorStore
            hits = VectorStore().search(query.strip(), int(limit or 5))
        except Exception as exc:
            log.warning("semantic_search failed: %s", exc)
            return ToolResult(ok=False, output=f"semantic search unavailable: {exc}")
        if not hits:
            return ToolResult(ok=True, output=f"No past conversation matches '{query}'.")
        lines = [f"- ({h['role']}) {h['content'][:200]}" for h in hits]
        return ToolResult(ok=True, output="Relevant past conversation:\n" + "\n".join(lines),
                          data={"count": len(hits)})
