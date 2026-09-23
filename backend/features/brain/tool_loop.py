"""AgenticToolLoop — multi-round tool-calling over plain JSON replies.

Protocol (works with ANY chat model, no native function-calling needed):
  model replies  {"tool": "...", "args": {...}}  -> loop executes, feeds result
  model replies  anything else                   -> final answer
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import List, Tuple

from ...core.config import MAX_TOOL_ROUNDS
from ...features.tools.registry import ToolRegistry
from .tool_parser import extract_json_objects, parse_json_call, parse_bracket_call, strip_calls

log = logging.getLogger("hinata.toolloop")


@dataclass
class TurnTrace:
    tool_calls: List[dict] = field(default_factory=list)

    def as_lines(self) -> List[str]:
        return [
            f"{c['tool']}({', '.join(f'{k}={v!r}' for k, v in c['args'].items())}) "
            f"-> {'ok' if c['ok'] else 'error'}"
            for c in self.tool_calls
        ]


class AgenticToolLoop:
    def __init__(self, tools: ToolRegistry) -> None:
        self.tools = tools

    def extract_call(self, text: str) -> dict | None:
        """Find a tool-call JSON object or bracket call in the reply."""
        candidate = text.strip()
        for blob in [candidate, *extract_json_objects(candidate)]:
            call = parse_json_call(blob, self.tools)
            if call:
                return call
        return parse_bracket_call(candidate, self.tools)

    def run(self, query: str, system: str, chat) -> Tuple[str, TurnTrace]:
        """Drive up to MAX_TOOL_ROUNDS tool rounds; returns (final_text, trace)."""
        self._chat = chat
        trace = TurnTrace()
        message = query
        final = ""
        seen_calls: set = set()

        for round_no in range(MAX_TOOL_ROUNDS + 1):
            reply = chat(system, message)
            call = self.extract_call(reply)
            if call is None or round_no == MAX_TOOL_ROUNDS:
                final = reply
                break

            tool_name = str(call.get("tool"))
            tool_args = dict(call.get("args") or {})
            sig = (tool_name, json.dumps(tool_args, sort_keys=True))

            if sig in seen_calls:
                final = self._force_final(system, tool_name)
                break
            seen_calls.add(sig)

            result = self.tools.dispatch(tool_name, tool_args)
            trace.tool_calls.append({
                "tool": tool_name, "args": tool_args,
                "ok": result.ok, "output": result.short(300),
            })
            message = self._next_message(query, result)

        final = self._finalize(strip_calls(final), trace)
        return final, trace

    def _force_final(self, system: str, tool_name: str) -> str:
        return self._chat(
            system,
            f"You already executed {tool_name}. Do NOT call any more tools.\n"
            f"Now give your direct spoken reply to the user in 1-2 natural sentences:",
        )

    @staticmethod
    def _next_message(query: str, result) -> str:
        if result.ok:
            return (
                f"Tool result:\n{result.short()}\n\n"
                f"Original request: {query}\n"
                "If you have everything you need, give the FINAL ANSWER as plain "
                "prose (no JSON, no brackets). Otherwise reply with exactly one next tool JSON."
            )
        return (
            f"Tool call failed: {result.short(200)}\n"
            "Fix the arguments and reply with exactly one tool JSON, or "
            "answer in plain prose without tools."
        )

    @staticmethod
    def _finalize(final: str, trace: TurnTrace) -> str:
        if final and final != "Done.":
            return final
        if trace.tool_calls:
            return f"I've completed that for you ({trace.tool_calls[-1]['tool']})."
        return "Understood!"
