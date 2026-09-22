"""ContextBuilder — assembles everything the brain needs per turn."""
from __future__ import annotations

from typing import List, Optional

from ...core.event_bus import EventBus
from ...features.tools.registry import ToolRegistry


class ContextBuilder:
    def __init__(self, bus: EventBus, tools: ToolRegistry) -> None:
        self.bus = bus
        self.tools = tools

    def user_context(self, query: str) -> str:
        """Memory history + KG associations relevant to this query."""
        blocks = []

        recent = self.bus.emit("memory.recent.query", {"limit": 10}).payload.get("turns") or []
        if recent:
            lines = [f"{'User' if t['role'] == 'user' else 'HINATA'}: {t['content'][:160]}"
                     for t in recent]
            blocks.append("Recent conversation:\n" + "\n".join(lines))

        kg = self.bus.emit("knowledge.context", {"hints": self._entities(query)}).payload
        if kg.get("block"):
            blocks.append(kg["block"])

        return "\n\n".join(blocks)

    def knowledge_context(self, query: str) -> dict:
        return self.bus.emit("knowledge.context", {"hints": self._entities(query)}).payload

    @staticmethod
    def _entities(text: str) -> List[str]:
        from ...features.knowledge.extractor import extract_entities
        return extract_entities(text)

    def system_prompt(self, soul: str, agentic: bool) -> str:
        """Persona + optional tool protocol."""
        prompt = soul
        if agentic:
            prompt += (
                "\n\n## Agentic tools\n"
                "You can act, not just talk. To use a tool, reply with ONLY this JSON "
                "(no prose, no markdown fence):\n"
                '{"tool": "<tool_name>", "args": {"<param>": "<value>"}}\n'
                "The system will run it and give you the result; then answer the user "
                "using the result. Tools available:\n"
                + self.tools.prompt_docs()
                + "\n\nUse tools whenever they make your answer factual or let you act. "
                  "If no tool is needed, just reply normally."
            )
        return prompt
