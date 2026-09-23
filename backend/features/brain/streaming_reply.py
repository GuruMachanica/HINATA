"""StreamingReply — streams the model, emitting speakable chunks as they form.

Used for the fast path (no tools): first TTS audio can start ~1-2s after the
user stops talking, while the model is still writing the rest of the answer.
"""
from __future__ import annotations

from typing import Callable, Dict, Optional

from ...core.config import STREAM_MIN_CHUNK_CHARS, STREAMING_ENABLED
from .stream_chunker import StreamChunker

import logging
log = logging.getLogger("hinata.stream")

# Callback(chunk_index, chunk_text, is_final)
ChunkCallback = Callable[[int, str, bool], None]


class StreamingReply:
    def __init__(self, engine, persona) -> None:
        self.engine = engine
        self.persona = persona

    def run(self, system: str, user_msg: str, on_chunk: Optional[ChunkCallback] = None) -> Dict:
        """Stream a reply; returns {reply, mood, streamed}."""
        if not STREAMING_ENABLED:
            text = self.engine.chat(system, user_msg)
            return self._result(text, streamed=False)

        chunker = StreamChunker(min_chars=STREAM_MIN_CHUNK_CHARS)
        parts: list = []
        chunk_idx = 0
        for delta in self.engine.chat_stream(system, user_msg):
            parts.append(delta)
            for chunk in chunker.feed(delta):
                if on_chunk:
                    on_chunk(chunk_idx, chunk, False)
                chunk_idx += 1
        tail = chunker.flush()
        if tail:
            if on_chunk:
                on_chunk(chunk_idx, tail, False)
            chunk_idx += 1

        full = "".join(parts)
        if not full.strip():
            log.warning("stream produced no content — nudge fallback")
            # Thinking overran the budget: zero content deltas. One nudge
            # completion lands a clean answer — speak it as a single chunk.
            full = self.engine.chat_raw(system, f"{user_msg}\n\n(Answer immediately in one short sentence. No deliberation.)")
            if full and on_chunk:
                on_chunk(0, full, False)
                chunk_idx += 1
        if on_chunk and chunk_idx > 0:
            on_chunk(chunk_idx, "", True)  # final marker
        return self._result(full, streamed=chunk_idx > 0)

    def _result(self, text: str, streamed: bool) -> Dict:
        mood = self.persona.detect_mood(text)
        clean = self.persona.strip_mood_tag(text)
        return {"reply": clean or "Understood!", "mood": mood, "streamed": streamed}
