"""File tools — read/list/write with sandboxing to the project root."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ....core.config import ROOT_DIR
from ..base import Tool, ToolParam, ToolResult, ToolRiskLevel

MAX_READ_BYTES = 20_000


def _safe_path(raw: str) -> Path | None:
    """Resolve inside ROOT_DIR only; blocks traversal outside the sandbox."""
    try:
        p = (ROOT_DIR / raw).resolve()
        return p if str(p).startswith(str(ROOT_DIR)) else None
    except (OSError, ValueError):
        return None


class ReadFileTool(Tool):
    name = "read_file"
    description = "Read a text file (relative to the HINATA project root)."
    risk_level = ToolRiskLevel.READ_ONLY
    params = [
        ToolParam("path", "string", "relative file path", required=True, min_len=1, max_len=300),
    ]

    def run(self, path: str = "", **_: Any) -> ToolResult:
        p = _safe_path(path)
        if not p or not p.is_file():
            return ToolResult(ok=False, output=f"not a readable file: {path}")
        try:
            text = p.read_text(encoding="utf-8", errors="replace")[:MAX_READ_BYTES]
            return ToolResult(ok=True, output=text, data={"path": str(p)})
        except OSError as exc:
            return ToolResult(ok=False, output=str(exc))


class ListDirTool(Tool):
    name = "list_dir"
    description = "List a directory (relative to the project root)."
    risk_level = ToolRiskLevel.READ_ONLY
    params = [
        ToolParam("path", "string", "relative directory path", required=False, min_len=1, max_len=300),
    ]

    def run(self, path: str = ".", **_: Any) -> ToolResult:
        p = _safe_path(path) or ROOT_DIR
        if not p.is_dir():
            return ToolResult(ok=False, output=f"not a directory: {path}")
        entries = sorted(
            (f"{e.name}/" if e.is_dir() else e.name) for e in p.iterdir()
        )[:200]
        return ToolResult(ok=True, output="\n".join(entries) or "(empty)")


class WriteFileTool(Tool):
    name = "write_file"
    description = "Write text to a file inside the project root (creates parents)."
    risk_level = ToolRiskLevel.MUTATING
    params = [
        ToolParam("path", "string", "relative file path inside project", required=True, min_len=1, max_len=300),
        ToolParam("content", "string", "text content to write", required=True, max_len=50_000),
    ]

    def run(self, path: str = "", content: str = "", **_: Any) -> ToolResult:
        p = _safe_path(path)
        if not p:
            return ToolResult(ok=False, output=f"blocked path outside sandbox: {path}")
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            return ToolResult(ok=True, output=f"wrote {len(content)} chars to {path}")
        except OSError as exc:
            return ToolResult(ok=False, output=str(exc))
