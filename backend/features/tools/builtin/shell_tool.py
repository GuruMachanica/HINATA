"""Shell and Python tools — strictly sandboxed with argument whitelisting and AST evaluation."""
from __future__ import annotations

import ast
import operator
import shlex
import subprocess
import sys
from typing import Any, Dict

from ..base import Tool, ToolParam, ToolResult, ToolRiskLevel

MAX_OUTPUT = 4000
DEFAULT_TIMEOUT = 20
MAX_TIMEOUT = 60

ALLOWED_COMMANDS = {
    "python", "py", "git", "pip", "dir", "echo", "type", "cat", "uptime", "whoami", "hostname",
}

DISALLOWED_CHARS = {"|", "&", ";", ">", "<", "`", "$", "\n", "\r"}


class ShellTool(Tool):
    name = "run_shell"
    description = (
        "Run a whitelisted diagnostic command (e.g. 'git status', 'pip list', 'python --version'). "
        "Arbitrary shell scripts, pipelines, and unapproved binaries are blocked."
    )
    risk_level = ToolRiskLevel.DANGEROUS
    params = [
        ToolParam("command", "string", "diagnostic command line to execute", required=True, min_len=1, max_len=500),
        ToolParam("timeout", "integer", "timeout in seconds (1 to 60)", required=False, min_val=1, max_val=MAX_TIMEOUT),
    ]

    def run(self, command: str = "", timeout: int = DEFAULT_TIMEOUT, **_: Any) -> ToolResult:
        cmd_str = command.strip()
        if not cmd_str:
            return ToolResult(ok=False, output="empty command")

        # Block shell chaining and redirection characters
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

        # Binary whitelist check
        binary = args[0].lower().rstrip(".exe")
        # Extract basename if path was provided
        if "/" in binary or "\\" in binary:
            import os
            binary = os.path.basename(binary)

        if binary not in ALLOWED_COMMANDS:
            return ToolResult(
                ok=False,
                output=(
                    f"security error: command '{args[0]}' is not in the allowed diagnostic whitelist "
                    f"({', '.join(sorted(ALLOWED_COMMANDS))})"
                ),
            )

        t_limit = max(1, min(int(timeout or DEFAULT_TIMEOUT), MAX_TIMEOUT))

        try:
            proc = subprocess.run(
                args,
                shell=False,
                capture_output=True,
                text=True,
                timeout=t_limit,
                encoding="utf-8",
                errors="replace",
            )
            out = (proc.stdout or "") + (f"\n[stderr]\n{proc.stderr}" if proc.stderr else "")
            status = "ok" if proc.returncode == 0 else f"exit {proc.returncode}"
            body = out.strip()[:MAX_OUTPUT] or "(no output)"
            return ToolResult(ok=proc.returncode == 0, output=f"[{status}] {body}")
        except subprocess.TimeoutExpired:
            return ToolResult(ok=False, output=f"command timed out after {t_limit}s")
        except Exception as exc:
            return ToolResult(ok=False, output=f"shell error: {exc}")


SAFE_FUNCTIONS: Dict[str, Any] = {
    "abs": abs,
    "min": min,
    "max": max,
    "round": round,
    "len": len,
    "sum": sum,
    "pow": pow,
    "sorted": sorted,
}

SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
    ast.Not: operator.not_,
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
    ast.In: lambda a, b: a in b,
    ast.NotIn: lambda a, b: a not in b,
}


class _SafeEvaluator(ast.NodeVisitor):
    def visit(self, node: ast.AST) -> Any:
        method = "visit_" + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node: ast.AST) -> Any:
        raise ValueError(f"operation '{node.__class__.__name__}' is not permitted in sandboxed Python")

    def visit_Expression(self, node: ast.Expression) -> Any:
        return self.visit(node.body)

    def visit_Constant(self, node: ast.Constant) -> Any:
        if isinstance(node.value, (int, float, str, bool, type(None))):
            return node.value
        raise ValueError(f"constant type '{type(node.value).__name__}' is not permitted")

    def visit_UnaryOp(self, node: ast.UnaryOp) -> Any:
        op_type = type(node.op)
        if op_type not in SAFE_OPERATORS:
            raise ValueError(f"unary operator '{op_type.__name__}' is not allowed")
        val = self.visit(node.operand)
        return SAFE_OPERATORS[op_type](val)

    def visit_BinOp(self, node: ast.BinOp) -> Any:
        op_type = type(node.op)
        if op_type not in SAFE_OPERATORS:
            raise ValueError(f"binary operator '{op_type.__name__}' is not allowed")
        left = self.visit(node.left)
        right = self.visit(node.right)
        if op_type == ast.Pow:
            if isinstance(right, (int, float)) and right > 10000:
                raise ValueError("exponent too large")
        return SAFE_OPERATORS[op_type](left, right)

    def visit_Compare(self, node: ast.Compare) -> Any:
        left = self.visit(node.left)
        for op, comparator in zip(node.ops, node.comparators):
            op_type = type(op)
            if op_type not in SAFE_OPERATORS:
                raise ValueError(f"comparison '{op_type.__name__}' is not allowed")
            right = self.visit(comparator)
            if not SAFE_OPERATORS[op_type](left, right):
                return False
            left = right
        return True

    def visit_List(self, node: ast.List) -> Any:
        return [self.visit(elt) for elt in node.elts]

    def visit_Tuple(self, node: ast.Tuple) -> Any:
        return tuple(self.visit(elt) for elt in node.elts)

    def visit_Dict(self, node: ast.Dict) -> Any:
        return {self.visit(k): self.visit(v) for k, v in zip(node.keys, node.values)}

    def visit_Name(self, node: ast.Name) -> Any:
        if node.id in SAFE_FUNCTIONS:
            return SAFE_FUNCTIONS[node.id]
        if node.id in ("True", "False", "None"):
            return {"True": True, "False": False, "None": None}[node.id]
        raise ValueError(f"name '{node.id}' is not defined or accessible")

    def visit_Call(self, node: ast.Call) -> Any:
        func = self.visit(node.func)
        if func not in SAFE_FUNCTIONS.values():
            raise ValueError("unauthorized function call")
        args = [self.visit(a) for a in node.args]
        return func(*args)


class PythonEvalTool(Tool):
    name = "run_python"
    description = (
        "Safely evaluate a mathematical or string Python expression (pure AST sandbox, "
        "no builtins, no file or system access)."
    )
    risk_level = ToolRiskLevel.DANGEROUS
    params = [
        ToolParam("code", "string", "safe mathematical or string expression", required=True, min_len=1, max_len=500),
    ]

    def run(self, code: str = "", **_: Any) -> ToolResult:
        expr = code.strip()
        if not expr:
            return ToolResult(ok=False, output="empty code expression")

        try:
            tree = ast.parse(expr, mode="eval")
            evaluator = _SafeEvaluator()
            val = evaluator.visit(tree)
            return ToolResult(ok=True, output=repr(val)[:MAX_OUTPUT])
        except Exception as exc:
            return ToolResult(ok=False, output=f"sandbox error: {exc}")
