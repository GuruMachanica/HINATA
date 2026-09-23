"""WSChatHandler — the /ws conversation flow (streaming + fallback)."""
from __future__ import annotations

import asyncio
import logging
from typing import Callable

from ...core.event_bus import EventBus
from .reply_events import send_result, speak_chunk, speak_full
from .state import ConnectionState

log = logging.getLogger("hinata.server")


async def _to_thread(fn, *args):
    return await asyncio.to_thread(fn, *args)


class WSChatHandler:
    def __init__(self, bus: EventBus, brain_think: Callable[[str], dict],
                 brain_think_stream: Callable | None = None) -> None:
        self.bus = bus
        self.brain_think = brain_think
        self.brain_think_stream = brain_think_stream
        self._chunk_idx = 0

    async def handle_chat(self, conn: ConnectionState, query: str) -> None:
        if not query.strip():
            return
        await conn.send_state("thinking")
        log.info("chat: %r (stream=%s)", query[:50], self.brain_think_stream is not None)
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
        """Fast path: sentence chunks stream out, TTS'd + played as they form."""
        main_loop = asyncio.get_running_loop()
        pending = []  # futures for scheduled chunk sends, awaited before reply

        def on_chunk(idx: int, text: str, is_final: bool) -> None:
            if not text:
                return
            self._chunk_idx += 1
            fut = asyncio.run_coroutine_threadsafe(
                speak_chunk(conn, text, self._chunk_idx), main_loop)
            pending.append(fut)

        result = await _to_thread(self.brain_think_stream, query, on_chunk)

        # Ensure every chunk TTS/send completed before the reply event so the
        # client never sees agent_response before her voice starts.
        for fut in pending:
            try:
                await asyncio.wrap_future(fut)
            except Exception as exc:
                log.warning("chunk send failed: %s", exc)

        await send_result(conn, result)
        await conn.send("speech_done", {"streamed": True})

    async def _classic(self, conn: ConnectionState, query: str) -> None:
        result = await _to_thread(self.brain_think, query)
        await send_result(conn, result)
        await speak_full(conn, result.get("reply") or "")
