"""BrainFeature — HINATA's mind: perceive, recall, act, speak, learn, emote."""
from __future__ import annotations

import time
from typing import Any, Dict, Optional

from ...core.base_feature import BaseFeature, register
from ...core.config import AGENTIC_MODE
from ...core.event_bus import Event
from .context_builder import ContextBuilder
from .hermes_engine import HermesEngine
from .persona import MOODS, Persona
from .tool_loop import AgenticToolLoop


@register
class BrainFeature(BaseFeature):
    name = "brain"

    def __init__(self) -> None:
        super().__init__()
        self.persona = Persona()
        self.engine = HermesEngine()
        self.agentic: Optional[AgenticToolLoop] = None
        self.context: Optional[ContextBuilder] = None

    def setup(self) -> None:
        # late imports avoid circulars; features resolve via package registry
        from ...features.tools.registry import load_builtin_tools
        tools = load_builtin_tools()
        self.agentic = AgenticToolLoop(tools)
        self.context = ContextBuilder(self.bus, tools)
        self.log.info("agentic mode=%s, tools=%d", AGENTIC_MODE, len(tools.all()))

    def think(self, query: str) -> Dict[str, Any]:
        """Full cognition cycle; returns reply + mood + trace + latency."""
        started = time.time()

        kg_payload = self.context.knowledge_context(query)
        system = self.context.system_prompt(self.persona.soul(), AGENTIC_MODE)
        user_msg = query
        ctx_block = self.context.user_context(query)
        if ctx_block:
            user_msg = f"{ctx_block}\n---\n\nUser: {query}"

        if AGENTIC_MODE:
            reply, trace = self.agentic.run(user_msg, system, self.engine.chat)
        else:
            reply, trace = self.engine.chat(system, user_msg), None

        mood = self.persona.detect_mood(reply)
        clean = self.persona.strip_mood_tag(reply)

        self._learn(query, clean, mood)
        return {
            "reply": clean,
            "mood": mood,
            "mood_meta": MOODS.get(mood, MOODS["neutral"]),
            "latency_ms": int((time.time() - started) * 1000),
            "trace": trace.as_lines() if trace else [],
            "kg_context_used": bool(kg_payload.get("block")),
        }

    def _learn(self, query: str, reply: str, mood: str) -> None:
        self.bus.emit("memory.append", {
            "role": "user", "content": query,
        }, source=self.name)
        self.bus.emit("memory.append", {
            "role": "assistant", "content": reply, "mood": mood,
        }, source=self.name)
        self.bus.emit("knowledge.observe", {
            "user_text": query, "reply": reply,
        }, source=self.name)
        self.bus.emit("hinata.spoke", {"reply": reply, "mood": mood}, source=self.name)

    # proactive engine pokes her brain with self-generated prompts
    def ponder(self, seed_prompt: str) -> Dict[str, Any]:
        return self.think(seed_prompt)

    def _unused(self, _event: Event) -> None:  # keeps Event import used
        pass
