"""Tool abstraction — every agentic capability implements this interface."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ToolRiskLevel(str, Enum):
    READ_ONLY = "read_only"
    MUTATING = "mutating"
    DANGEROUS = "dangerous"


@dataclass
class ToolParam:
    name: str
    type: str = "string"  # "string" | "integer" | "number" | "boolean"
    description: str = ""
    required: bool = True
    min_val: Optional[float] = None
    max_val: Optional[float] = None
    min_len: Optional[int] = None
    max_len: Optional[int] = None
    choices: Optional[List[Any]] = None


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
    risk_level: ToolRiskLevel = ToolRiskLevel.READ_ONLY

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
            if p.name in kwargs:
                val = kwargs[p.name]
                if val is None and p.required:
                    return f"param '{p.name}' cannot be null"
                if val is None:
                    continue

                # Type checks & bounds
                if p.type == "integer":
                    try:
                        int_val = int(val)
                    except (ValueError, TypeError):
                        return f"param '{p.name}' must be an integer (got {type(val).__name__})"
                    if p.min_val is not None and int_val < p.min_val:
                        return f"param '{p.name}' must be >= {p.min_val} (got {int_val})"
                    if p.max_val is not None and int_val > p.max_val:
                        return f"param '{p.name}' must be <= {p.max_val} (got {int_val})"
                    kwargs[p.name] = int_val

                elif p.type in ("number", "float"):
                    try:
                        float_val = float(val)
                    except (ValueError, TypeError):
                        return f"param '{p.name}' must be a number (got {type(val).__name__})"
                    if p.min_val is not None and float_val < p.min_val:
                        return f"param '{p.name}' must be >= {p.min_val} (got {float_val})"
                    if p.max_val is not None and float_val > p.max_val:
                        return f"param '{p.name}' must be <= {p.max_val} (got {float_val})"
                    kwargs[p.name] = float_val

                elif p.type == "string":
                    if not isinstance(val, str):
                        val = str(val)
                        kwargs[p.name] = val
                    if p.min_len is not None and len(val) < p.min_len:
                        return f"param '{p.name}' length must be >= {p.min_len}"
                    if p.max_len is not None and len(val) > p.max_len:
                        return f"param '{p.name}' length must be <= {p.max_len}"

                if p.choices is not None and val not in p.choices:
                    return f"param '{p.name}' must be one of {p.choices} (got '{val}')"

        return None
