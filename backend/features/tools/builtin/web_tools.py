"""Web tools — live internet searching via DuckDuckGo."""
from __future__ import annotations

import logging
from typing import Any

from ..base import Tool, ToolParam, ToolResult

log = logging.getLogger("hinata.tools.web")


class WebSearchTool(Tool):
    name = "web_search"
    description = (
        "Search the live internet for real-time information, current facts, "
        "news, documentation, websites, or answers."
    )
    params = [
        ToolParam("query", "string", "The search query to look up on the web"),
        ToolParam("count", "integer", "Number of results to return (default 4)", required=False),
    ]

    def run(self, query: str = "", count: int = 4, **kwargs: Any) -> ToolResult:
        if not query or not query.strip():
            return ToolResult(ok=False, output="Empty search query")

        clean_query = query.strip()
        safe_limit = max(1, min(int(count or 4), 8))

        try:
            try:
                from ddgs import DDGS
            except ImportError:
                from duckduckgo_search import DDGS  # type: ignore

            results = []
            with DDGS(timeout=10) as client:
                for hit in client.text(clean_query, max_results=safe_limit):
                    title = hit.get("title", "").strip()
                    url = (hit.get("href") or hit.get("url") or "").strip()
                    body = hit.get("body", "").strip()
                    results.append(f"- **{title}**\n  URL: {url}\n  Summary: {body}")

            if not results:
                return ToolResult(ok=True, output=f"No web results found for: {clean_query}")

            output = f"Web search results for '{clean_query}':\n\n" + "\n\n".join(results)
            return ToolResult(ok=True, output=output, data={"count": len(results), "query": clean_query})

        except Exception as exc:
            log.warning("Web search failed for '%s': %s", clean_query, exc)
            return ToolResult(ok=False, output=f"Web search failed: {exc}")
