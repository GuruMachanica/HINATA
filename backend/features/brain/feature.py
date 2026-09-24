"""BrainFeature — HINATA's mind: perceive, recall, act, speak, learn, emote."""
from __future__ import annotations

import threading
import time
from typing import Any, Dict, Optional

from ...core.base_feature import BaseFeature, register
from ...core.config import AGENTIC_MODE
from ...core.event_bus import Event
from .context_builder import ContextBuilder
from .hermes_engine import HermesEngine
from .persona import MOODS, Persona
from .streaming_reply import StreamingReply
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
        self._think_lock = threading.Lock()

    def setup(self) -> None:
        from ...features.tools.registry import load_builtin_tools
        tools = load_builtin_tools()
        self.agentic = AgenticToolLoop(tools)
        self.context = ContextBuilder(self.bus, tools)
        self.engine.wire_router()
        self.log.info("agentic mode=%s, tools=%d", AGENTIC_MODE, len(tools.all()))

    def think(self, query: str) -> Dict[str, Any]:
        """Full cognition cycle with serialized model inference; returns reply + mood + trace + latency."""
        started = time.time()

        with self._think_lock:
            ctx_block, kg_used = self.context.user_context_bundle(query)
            system = self.context.system_prompt(self.persona.soul(), AGENTIC_MODE)
            user_msg = f"{ctx_block}\n---\n\nUser: {query}" if ctx_block else query

            if AGENTIC_MODE:
                # Tool loop drives single completions (engine.chat_raw): the
                # full Hermes agent's auto-continuation confabulates on 2B
                # thinking models. Hermes stays available via engine.chat().
                reply, trace = self.agentic.run(user_msg, system, self.engine.chat_raw)
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
                "kg_context_used": kg_used,
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

    def think_stream(self, query: str, on_chunk) -> Dict[str, Any]:
        """Streaming cognition: chunks speak as they form; returns full result."""
        started = time.time()
        with self._think_lock:
            ctx_block, kg_used = self.context.user_context_bundle(query)
            system = self.context.system_prompt(self.persona.soul(), False)  # no tool JSON in stream
            user_msg = f"{ctx_block}\n---\n\nUser: {query}" if ctx_block else query

            streamer = StreamingReply(self.engine, self.persona)
            result = streamer.run(system, user_msg, on_chunk)

            self._learn(query, result["reply"], result["mood"])
            result.update({
                "latency_ms": int((time.time() - started) * 1000),
                "trace": [],
                "kg_context_used": kg_used,
                "mood_meta": MOODS.get(result["mood"], MOODS["neutral"]),
            })
            return result

    # proactive engine pokes her brain with self-generated prompts
    def ponder(self, seed_prompt: str) -> Dict[str, Any]:
        return self.think(seed_prompt)

    def _unused(self, _event: Event) -> None:
        pass
