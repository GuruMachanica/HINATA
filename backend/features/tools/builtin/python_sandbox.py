"""AST sandbox for evaluating pure Python expressions safely.

No builtins, no attribute access, no imports — only whitelisted
functions, operators and literal containers.
"""
from __future__ import annotations

import ast
import operator
from typing import Any, Dict

SAFE_FUNCTIONS: Dict[str, Any] = {
    "abs": abs, "min": min, "max": max, "round": round,
    "len": len, "sum": sum, "pow": pow, "sorted": sorted,
}

SAFE_OPERATORS = {
    ast.Add: operator.add, ast.Sub: operator.sub,
    ast.Mult: operator.mul, ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod,
    ast.Pow: operator.pow, ast.USub: operator.neg,
    ast.UAdd: operator.pos, ast.Not: operator.not_,
    ast.Eq: operator.eq, ast.NotEq: operator.ne,
    ast.Lt: operator.lt, ast.LtE: operator.le,
    ast.Gt: operator.gt, ast.GtE: operator.ge,
    ast.In: lambda a, b: a in b, ast.NotIn: lambda a, b: a not in b,
}

_CONST_NAMES = {"True": True, "False": False, "None": None}


class SafeEvaluator(ast.NodeVisitor):
    def visit(self, node: ast.AST) -> Any:
        visitor = getattr(self, "visit_" + node.__class__.__name__, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node: ast.AST) -> Any:
        raise ValueError(
            f"operation '{node.__class__.__name__}' is not permitted in sandboxed Python"
        )

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
        return SAFE_OPERATORS[op_type](self.visit(node.operand))

    def visit_BinOp(self, node: ast.BinOp) -> Any:
        op_type = type(node.op)
        if op_type not in SAFE_OPERATORS:
            raise ValueError(f"binary operator '{op_type.__name__}' is not allowed")
        left, right = self.visit(node.left), self.visit(node.right)
        if op_type == ast.Pow and isinstance(right, (int, float)) and right > 10000:
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
        if node.id in _CONST_NAMES:
            return _CONST_NAMES[node.id]
        raise ValueError(f"name '{node.id}' is not defined or accessible")

    def visit_Call(self, node: ast.Call) -> Any:
        func = self.visit(node.func)
        if func not in SAFE_FUNCTIONS.values():
            raise ValueError("unauthorized function call")
        args = [self.visit(a) for a in node.args]
        return func(*args)


def safe_eval(expr: str) -> Any:
    """Parse and evaluate a pure expression; raises on anything unsafe."""
    tree = ast.parse(expr, mode="eval")
    return SafeEvaluator().visit(tree)
