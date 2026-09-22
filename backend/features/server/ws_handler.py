"""WSChatHandler — the /ws conversation flow."""
from __future__ import annotations

from typing import Callable, Dict

from ...core.event_bus import EventBus
from .state import ConnectionState


class WSChatHandler:
    def __init__(self, bus: EventBus, brain_think: Callable[[str], dict]) -> None:
        self.bus = bus
        self.brain_think = brain_think

    async def handle_chat(self, conn: ConnectionState, query: str) -> None:
        if not query.strip():
            return
        await conn.send_state("thinking")
        result = await _to_thread(self.brain_think, query)

        await conn.send_state("speaking")
        await conn.send("agent_response", {
            "content": result["reply"], "mood": result["mood"],
            "latency_ms": result["latency_ms"],
        })
        if result.get("trace"):
            await conn.send("tool_trace", {"calls": result["trace"]})
        meta = result["mood_meta"]
        await conn.send("avatar_mood", {
            "mood": result["mood"], "expression": meta["expression"],
            "behavior": meta.get("behavior"),
        })
        await conn.send_state("online")


async def _to_thread(fn, *args):
    import asyncio
    return await asyncio.to_thread(fn, *args)
