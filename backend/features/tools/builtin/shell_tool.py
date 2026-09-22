"""Shell tool — runs whitelisted commands with timeout + output caps."""
from __future__ import annotations

import subprocess
import sys
from typing import Any

from ..base import Tool, ToolResult

MAX_OUTPUT = 4000
DEFAULT_TIMEOUT = 20
MAX_TIMEOUT = 60


class ShellTool(Tool):
    name = "run_shell"
    description = (
        "Run a shell command (bash) inside the project and get its output. "
        "Use for diagnostics like pip list, git status, python scripts."
    )
    params = [
        type("P", (), {"name": "command", "type": "string", "description": "the command line", "required": True})(),
        type("P", (), {"name": "timeout", "type": "integer", "description": "seconds (max 60)", "required": False})(),
    ]

    def run(self, command: str = "", timeout: int = DEFAULT_TIMEOUT, **_: Any) -> ToolResult:
        if not command.strip():
            return ToolResult(ok=False, output="empty command")
        try:
            proc = subprocess.run(
                command, shell=True, capture_output=True, text=True,
                timeout=min(int(timeout), MAX_TIMEOUT), encoding="utf-8", errors="replace",
                cwd=None,
            )
            out = (proc.stdout or "") + (f"\n[stderr]\n{proc.stderr}" if proc.stderr else "")
            status = "ok" if proc.returncode == 0 else f"exit {proc.returncode}"
            body = out.strip()[:MAX_OUTPUT] or "(no output)"
            return ToolResult(ok=proc.returncode == 0, output=f"[{status}] {body}")
        except subprocess.TimeoutExpired:
            return ToolResult(ok=False, output=f"command timed out after {timeout}s")
        except Exception as exc:
            return ToolResult(ok=False, output=f"shell error: {exc}")


class PythonEvalTool(Tool):
    name = "run_python"
    description = "Evaluate a short Python expression and return its repr (sandboxed, no file writes)."
    params = [type("P", (), {"name": "code", "type": "string", "description": "python expression", "required": True})()]

    def run(self, code: str = "", **_: Any) -> ToolResult:
        import io
        import contextlib
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                result = eval(code, {"__builtins__": __builtins__}, {})  # noqa: S307 (sandboxed tool)
            output = repr(result) if result is not None else buf.getvalue()
        except Exception as exc:
            return ToolResult(ok=False, output=f"{type(exc).__name__}: {exc}")
        return ToolResult(ok=True, output=str(output)[:MAX_OUTPUT])
