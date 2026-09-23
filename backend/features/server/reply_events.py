"""WS reply helpers — voice synthesis + result event emission for chat paths."""
from __future__ import annotations

import asyncio
import logging

from .state import ConnectionState

log = logging.getLogger("hinata.server")


async def send_result(conn: ConnectionState, result: dict) -> None:
    """Emit agent_response + tool_trace + avatar_mood for a finished turn."""
    await conn.send_state("speaking")
    await conn.send("agent_response", {
        "content": result.get("reply") or "Understood.",
        "mood": result.get("mood", "calm"),
        "latency_ms": result.get("latency_ms", 0),
        "streamed": result.get("streamed", False),
    })
    if result.get("trace"):
        await conn.send("tool_trace", {"calls": result["trace"]})
    meta = result.get("mood_meta") or {"expression": "neutral"}
    await conn.send("avatar_mood", {
        "mood": result.get("mood", "calm"),
        "expression": meta.get("expression", "neutral"),
        "behavior": meta.get("behavior"),
    })


def voice_feature():
    from ...features.voice import VoiceFeature
    from ...core.base_feature import get
    return get(VoiceFeature.name)


async def _tts(text: str):
    """Run the (blocking) synthesizer off the event loop."""
    return await asyncio.to_thread(voice_feature().synthesize, text)


async def speak_chunk(conn: ConnectionState, text: str, index: int) -> bool:
    """Synthesize one sentence chunk; send speech_chunk with audio. True on success."""
    try:
        audio_uri = await _tts(text)
        if not audio_uri:
            return False
        log.info("speech_chunk #%d sent (%d chars)", index, len(text))
        await conn.send("speech_chunk", {"text": text, "audio": audio_uri, "index": index})
        return True
    except Exception as exc:
        log.warning("chunk TTS failed: %s", exc)
        return False


async def speak_full(conn: ConnectionState, text: str) -> None:
    """Synthesize a whole reply and send it as a single audio chunk."""
    if not text:
        return
    try:
        audio_uri = await _tts(text)
        if audio_uri:
            await conn.send("speech_chunk", {"text": text, "audio": audio_uri})
    except Exception as exc:
        log.warning("TTS synthesis failed: %s", exc)
