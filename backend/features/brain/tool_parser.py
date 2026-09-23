"""Tool-call parsing — extracts JSON or bracket-style tool calls from model replies."""
from __future__ import annotations

import ast
import json
import re
from typing import List, Optional

_TOOL_KEY_RE = re.compile(r"\"tool\"\s*:")


def extract_json_objects(text: str) -> List[str]:
    """Pull balanced {...} objects containing a "tool" key."""
    out = []
    for start in (m.start() for m in _TOOL_KEY_RE.finditer(text)):
        begin = text.rfind("{", 0, start + 1)
        if begin < 0:
            continue
        depth = 0
        for i in range(begin, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    out.append(text[begin:i + 1])
                    break
    return out


def parse_json_call(blob: str, registry) -> Optional[dict]:
    """Parse a JSON blob as a tool call if possible; returns normalized dict or None."""
    try:
        parsed = json.loads(blob)
    except json.JSONDecodeError:
        return None
    if isinstance(parsed, dict) and "tool" in parsed:
        parsed["tool"] = str(parsed["tool"]).replace("()", "").strip()
        return parsed
    return None


def parse_bracket_call(text: str, registry) -> Optional[dict]:
    """Detect calls like [web_search(\"query\")] or get_time() in plain prose."""
    for m in re.finditer(r"\[([a-zA-Z_0-9]+)\s*\((.*?)\)\s*\]", text, re.DOTALL):
        call = _match_call(m.group(1), m.group(2), registry)
        if call:
            return call
    return None


def _match_call(fn_name: str, args_raw: str, registry) -> Optional[dict]:
    tool = registry.get(fn_name.strip())
    if not tool:
        return None
    return {"tool": fn_name.strip(), "args": _parse_call_args(args_raw.strip(), tool)}


def _parse_call_args(args_raw: str, tool) -> dict:
    if not args_raw:
        return {}
    kwargs: dict = {}
    positional: list = []
    try:
        tree = ast.parse(f"f({args_raw})").body[0].value  # type: ignore
        for arg in tree.args:
            positional.append(ast.literal_eval(arg))
        for kw in tree.keywords:
            kwargs[kw.arg] = ast.literal_eval(kw.value)
    except Exception:
        cleaned = args_raw.strip().strip("'\"")
        if cleaned:
            positional.append(cleaned)

    if positional:
        param_names = [p.name for p in tool.params]
        for name, val in zip(param_names, positional):
            if name not in kwargs:
                kwargs[name] = val
    return kwargs


def strip_calls(text: str) -> str:
    """Remove tool-call JSON blobs, bracket calls, and stray formatting artifacts."""
    cleaned = text
    for blob in extract_json_objects(text):
        cleaned = cleaned.replace(blob, "")
    cleaned = re.sub(r"<tool>.*?</tool>", "", cleaned, flags=re.DOTALL)
    cleaned = re.sub(r"\[[a-zA-Z_0-9]+\s*\([^\]]*\)\s*\]", "", cleaned)
    cleaned = re.sub(r"\*\*(\s*)\*\*", r"\1", cleaned)
    cleaned = re.sub(r"(?:^|\s)\*\*(?:\s|$)", " ", cleaned)
    return cleaned.strip() or "Done."
