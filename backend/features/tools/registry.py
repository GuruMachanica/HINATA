"""ToolRegistry — discovers, validates, and dispatches tools.

Every tool runs in isolation: an exception becomes ok=False result,
never a crashed request.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Type

from .base import Tool, ToolResult

log = logging.getLogger("hinata.tools")


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> Tool:
        self._tools[tool.name] = tool
        log.info("tool registered: %s", tool.signature())
        return tool

    def register_all(self, *tools: Tool) -> None:
        for t in tools:
            self.register(t)

    def get(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def all(self) -> List[Tool]:
        return list(self._tools.values())

    def prompt_docs(self) -> str:
        return "\n".join(t.doc_line() for t in self._tools.values())

    def dispatch(self, name: str, kwargs: Dict[str, Any]) -> ToolResult:
        tool = self._tools.get(name)
        if not tool:
            return ToolResult(ok=False, output=f"unknown tool '{name}'")
        err = tool.validate(kwargs)
        if err:
            return ToolResult(ok=False, output=f"{name}: {err}")
        try:
            return tool.run(**kwargs)
        except Exception as exc:  # isolation
            log.exception("tool %s crashed", name)
            return ToolResult(ok=False, output=f"tool '{name}' failed: {exc}")

    def dispatch_json(self, blob: str) -> ToolResult:
        """Parse a tool-call JSON blob: {"tool": "...", "args": {...}}."""
        try:
            parsed = json.loads(blob)
            return self.dispatch(str(parsed.get("tool")), dict(parsed.get("args") or {}))
        except json.JSONDecodeError as exc:
            return ToolResult(ok=False, output=f"bad tool-call JSON: {exc}")


registry = ToolRegistry()


def load_builtin_tools() -> ToolRegistry:
    """Import builtins so their registration side-effects run."""
    from . import builtin  # noqa: F401  (registers on import)
    return registry
