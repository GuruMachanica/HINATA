"""Tool abstraction — every agentic capability implements this interface."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class ToolParam:
    name: str
    type: str = "string"
    description: str = ""
    required: bool = True


@dataclass
class ToolResult:
    ok: bool
    output: str
    data: Dict[str, Any] = field(default_factory=dict)

    def short(self, limit: int = 1500) -> str:
        return self.output[:limit] + ("…[truncated]" if len(self.output) > limit else "")


class Tool(ABC):
    """Base class: subclass, set name/description/params, implement run()."""

    name: str = "tool"
    description: str = ""
    params: List[ToolParam] = []

    @abstractmethod
    def run(self, **kwargs: Any) -> ToolResult:
        """Execute the tool; must never raise — return ok=False on failure."""

    # -- prompt-schema helpers ------------------------------------------------
    def signature(self) -> str:
        args = ", ".join(f"{p.name}: {p.type}" + ("" if p.required else "?") for p in self.params)
        return f"{self.name}({args})"

    def doc_line(self) -> str:
        return f"- {self.signature()}: {self.description}"

    def validate(self, kwargs: Dict[str, Any]) -> str | None:
        for p in self.params:
            if p.required and p.name not in kwargs:
                return f"missing required param '{p.name}'"
        return None
