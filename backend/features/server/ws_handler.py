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
        try:
            result = await _to_thread(self.brain_think, query)

            await conn.send_state("speaking")
            await conn.send("agent_response", {
                "content": result.get("reply") or "Understood.",
                "mood": result.get("mood", "calm"),
                "latency_ms": result.get("latency_ms", 0),
            })
            if result.get("trace"):
                await conn.send("tool_trace", {"calls": result["trace"]})
            meta = result.get("mood_meta") or {"expression": "neutral"}
            await conn.send("avatar_mood", {
                "mood": result.get("mood", "calm"),
                "expression": meta.get("expression", "neutral"),
                "behavior": meta.get("behavior"),
            })

            # Voice synthesis — stream speech_chunk to frontend and desktop overlay
            try:
                from ...features.voice import VoiceFeature
                from ...core.base_feature import get
                voice: VoiceFeature = get(VoiceFeature.name)
                if voice and result.get("reply"):
                    audio_uri = await _to_thread(voice.synthesize, result["reply"])
                    if audio_uri:
                        await conn.send("speech_chunk", {
                            "text": result["reply"],
                            "audio": audio_uri,
                        })
            except Exception as exc:
                import logging
                logging.getLogger("hinata.server").warning("TTS synthesis failed: %s", exc)

        except Exception as exc:
            import logging
            logging.getLogger("hinata.server").exception("handle_chat failed: %s", exc)
            await conn.send("agent_response", {
                "content": "I ran into a temporary hitch, but I'm back online. Could you repeat that?",
                "mood": "concerned",
                "latency_ms": 0,
            })
        finally:
            await conn.send_state("online")


async def _to_thread(fn, *args):
    import asyncio
    return await asyncio.to_thread(fn, *args)
