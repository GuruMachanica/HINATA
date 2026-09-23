"""Shell and Python tools — strictly sandboxed with argument whitelisting and AST evaluation."""
from __future__ import annotations

import os
import shlex
import subprocess
from typing import Any

from ..base import Tool, ToolParam, ToolResult, ToolRiskLevel
from .python_sandbox import safe_eval
from .shell_allowlist import ALLOWED_COMMANDS, DISALLOWED_CHARS

MAX_OUTPUT = 4000
DEFAULT_TIMEOUT = 20
MAX_TIMEOUT = 60


class ShellTool(Tool):
    name = "run_shell"
    description = (
        "Run a whitelisted diagnostic command (e.g. 'git status', 'pip list', 'python --version'). "
        "Arbitrary shell scripts, pipelines, and unapproved binaries are blocked."
    )
    risk_level = ToolRiskLevel.DANGEROUS
    params = [
        ToolParam("command", "string", "diagnostic command line to execute",
                  required=True, min_len=1, max_len=500),
        ToolParam("timeout", "integer", "timeout in seconds (1 to 60)",
                  required=False, min_val=1, max_val=MAX_TIMEOUT),
    ]

    def run(self, command: str = "", timeout: int = DEFAULT_TIMEOUT, **_: Any) -> ToolResult:
        cmd_str = command.strip()
        if not cmd_str:
            return ToolResult(ok=False, output="empty command")

        for ch in DISALLOWED_CHARS:
            if ch in cmd_str:
                return ToolResult(
                    ok=False,
                    output=f"security error: operator '{ch}' is not allowed in commands",
                )

        try:
            args = shlex.split(cmd_str, posix=False)
        except Exception as exc:
            return ToolResult(ok=False, output=f"invalid command syntax: {exc}")

        if not args:
            return ToolResult(ok=False, output="empty command arguments")

        binary = self._binary_name(args[0])
        if binary not in ALLOWED_COMMANDS:
            return ToolResult(
                ok=False,
                output=(
                    f"security error: command '{args[0]}' is not in the allowed diagnostic "
                    f"whitelist ({', '.join(sorted(ALLOWED_COMMANDS))})"
                ),
            )

        return self._execute(args, max(1, min(int(timeout or DEFAULT_TIMEOUT), MAX_TIMEOUT)))

    @staticmethod
    def _binary_name(raw: str) -> str:
        binary = raw.lower().rstrip(".exe")
        if "/" in binary or "\\" in binary:
            binary = os.path.basename(binary)
        return binary

    @staticmethod
    def _execute(args: list, t_limit: int) -> ToolResult:
        try:
            proc = subprocess.run(
                args, shell=False, capture_output=True, text=True,
                timeout=t_limit, encoding="utf-8", errors="replace",
            )
            out = (proc.stdout or "") + (f"\n[stderr]\n{proc.stderr}" if proc.stderr else "")
            status = "ok" if proc.returncode == 0 else f"exit {proc.returncode}"
            body = out.strip()[:MAX_OUTPUT] or "(no output)"
            return ToolResult(ok=proc.returncode == 0, output=f"[{status}] {body}")
        except subprocess.TimeoutExpired:
            return ToolResult(ok=False, output=f"command timed out after {t_limit}s")
        except Exception as exc:
            return ToolResult(ok=False, output=f"shell error: {exc}")


class PythonEvalTool(Tool):
    name = "run_python"
    description = (
        "Safely evaluate a mathematical or string Python expression (pure AST sandbox, "
        "no builtins, no file or system access)."
    )
    risk_level = ToolRiskLevel.DANGEROUS
    params = [
        ToolParam("code", "string", "safe mathematical or string expression",
                  required=True, min_len=1, max_len=500),
    ]

    def run(self, code: str = "", **_: Any) -> ToolResult:
        expr = code.strip()
        if not expr:
            return ToolResult(ok=False, output="empty code expression")
        try:
            val = safe_eval(expr)
            return ToolResult(ok=True, output=repr(val)[:MAX_OUTPUT])
        except Exception as exc:
            return ToolResult(ok=False, output=f"sandbox error: {exc}")
