"""AgenticToolLoop — multi-round tool-calling over plain JSON replies.

Protocol (works with ANY chat model, no native function-calling needed):
  model replies  {"tool": "...", "args": {...}}  -> loop executes, feeds result
  model replies  anything else                   -> final answer
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import List

from ...core.config import MAX_TOOL_ROUNDS
from ...features.tools.registry import ToolRegistry

log = logging.getLogger("hinata.toolloop")

_JSON_RE = re.compile(r"\{\s*\"tool\".*?\}\s*$|\{\s*\"tool\".*?\}", re.DOTALL)
_TOOL_KEY_RE = re.compile(r"\"tool\"\s*:")


def _extract_json_objects(text: str) -> List[str]:
    """Pull balanced {...} objects containing a \"tool\" key."""
    out = []
    for start in (m.start() for m in _TOOL_KEY_RE.finditer(text)):
        depth = 0
        begin = text.rfind("{", 0, start + 1)
        if begin < 0:
            continue
        for i in range(begin, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    out.append(text[begin:i + 1])
                    break
    return out


@dataclass
class TurnTrace:
    tool_calls: List[dict] = field(default_factory=list)

    def as_lines(self) -> List[str]:
        return [
            f"{c['tool']}({', '.join(f'{k}={v!r}' for k, v in c['args'].items())}) "
            f"-> {'ok' if c['ok'] else 'error'}"
            for c in self.tool_calls
        ]


def _strip_calls(text: str) -> str:
    """Remove tool-call JSON blobs from a final answer."""
    cleaned = text
    for blob in _extract_json_objects(text):
        cleaned = cleaned.replace(blob, "")
    return cleaned.strip() or "Done."


class AgenticToolLoop:
    def __init__(self, tools: ToolRegistry) -> None:
        self.tools = tools

    @staticmethod
    def extract_call(text: str) -> dict | None:
        """Find a tool-call JSON object in the reply (strict or embedded)."""
        candidate = text.strip()
        blobs = [candidate, *_extract_json_objects(candidate)]
        for blob in blobs:
            try:
                parsed = json.loads(blob)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict) and "tool" in parsed:
                parsed["tool"] = str(parsed["tool"]).replace("()", "").strip()
                return parsed
        return None

    def run(self, query: str, system: str, chat) -> tuple[str, TurnTrace]:
        """Drive up to MAX_TOOL_ROUNDS tool rounds; returns (final_text, trace)."""
        trace = TurnTrace()
        message = query
        final = ""

        for _round in range(MAX_TOOL_ROUNDS + 1):
            reply = chat(system, message)
            call = self.extract_call(reply)
            if call is None or _round == MAX_TOOL_ROUNDS:
                final = reply
                break
            result = self.tools.dispatch(str(call.get("tool")), dict(call.get("args") or {}))
            trace.tool_calls.append({
                "tool": call.get("tool"), "args": call.get("args") or {},
                "ok": result.ok, "output": result.short(300),
            })
            if result.ok:
                message = (
                    f"Tool result:\n{result.short()}\n\n"
                    f"Original request: {query}\n"
                    "If you have everything you need, give the FINAL ANSWER as plain "
                    "prose (no JSON). Otherwise reply with exactly one next tool JSON."
                )
            else:
                message = (
                    f"Tool call failed: {result.short(200)}\n"
                    "Fix the arguments and reply with exactly one tool JSON, or "
                    "answer in plain prose without tools."
                )

        final = _strip_calls(final)
        return final, trace
