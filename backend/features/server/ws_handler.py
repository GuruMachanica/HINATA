"""WSChatHandler — the /ws conversation flow (streaming + fallback)."""
from __future__ import annotations

import asyncio
import logging
from typing import Callable

from ...core.event_bus import EventBus
from .state import ConnectionState

log = logging.getLogger("hinata.server")


class WSChatHandler:
    def __init__(self, bus: EventBus, brain_think: Callable[[str], dict],
                 brain_think_stream: Callable | None = None) -> None:
        self.bus = bus
        self.brain_think = brain_think
        self.brain_think_stream = brain_think_stream

    async def handle_chat(self, conn: ConnectionState, query: str) -> None:
        if not query.strip():
            return
        await conn.send_state("thinking")
        try:
            if self.brain_think_stream:
                await self._streamed(conn, query)
            else:
                await self._classic(conn, query)
        except Exception as exc:
            log.exception("handle_chat failed: %s", exc)
            await conn.send("agent_response", {
                "content": "I ran into a temporary hitch, but I'm back online. Could you repeat that?",
                "mood": "concerned", "latency_ms": 0,
            })
        finally:
            await conn.send_state("online")

    async def _streamed(self, conn: ConnectionState, query: str) -> None:
        """Fast path: sentence chunks stream out (and get TTS'd) as they form."""
        loop = asyncio.get_event_loop()

        def on_chunk(idx: int, text: str, is_final: bool) -> None:
            if text:
                asyncio.run_coroutine_threadsafe(
                    conn.send("speech_chunk", {"text": text, "index": idx}), loop)

        result = await _to_thread(self.brain_think_stream, query, on_chunk)

        await conn.send_state("speaking")
        await conn.send("agent_response", {
            "content": result.get("reply") or "Understood.",
            "mood": result.get("mood", "calm"),
            "latency_ms": result.get("latency_ms", 0),
            "streamed": result.get("streamed", False),
        })
        if result.get("trace"):
            await conn.send("tool_trace", {"calls": result["trace"]})
        await self._mood(conn, result)
        # TTS is dispatched per-chunk inside brain_think_stream; audio_uri events
        # were already pushed as speech_audio with matching index.
        await conn.send("speech_done", {"streamed": True})

    async def _classic(self, conn: ConnectionState, query: str) -> None:
        result = await _to_thread(self.brain_think, query)
        await conn.send_state("speaking")
        await conn.send("agent_response", {
            "content": result.get("reply") or "Understood.",
            "mood": result.get("mood", "calm"),
            "latency_ms": result.get("latency_ms", 0),
        })
        if result.get("trace"):
            await conn.send("tool_trace", {"calls": result["trace"]})
        await self._mood(conn, result)
        await self._voice(conn, result.get("reply") or "")

    async def _mood(self, conn: ConnectionState, result: dict) -> None:
        meta = result.get("mood_meta") or {"expression": "neutral"}
        await conn.send("avatar_mood", {
            "mood": result.get("mood", "calm"),
            "expression": meta.get("expression", "neutral"),
            "behavior": meta.get("behavior"),
        })

    async def _voice(self, conn: ConnectionState, reply: str) -> None:
        if not reply:
            return
        try:
            from ...features.voice import VoiceFeature
            from ...core.base_feature import get
            voice: VoiceFeature = get(VoiceFeature.name)
            audio_uri = await _to_thread(voice.synthesize, reply)
            if audio_uri:
                await conn.send("speech_chunk", {"text": reply, "audio": audio_uri})
        except Exception as exc:
            log.warning("TTS synthesis failed: %s", exc)


async def _to_thread(fn, *args):
    return await asyncio.to_thread(fn, *args)
