"""SentenceChunker — splits a token stream into speakable sentence chunks."""
from __future__ import annotations

import re
from typing import List

_SENT_END = re.compile(r"(?<=[.!?])\s+")

# Abbreviations that should NOT end a sentence
_ABBREV = ("mr.", "mrs.", "ms.", "dr.", "e.g.", "i.e.", "vs.", "etc.", "st.")


def split_sentences(text: str) -> List[str]:
    parts = _SENT_END.split(text.strip())
    merged: List[str] = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        # merge fragments that end with an abbreviation with the next part
        if merged and merged[-1].lower().endswith(_ABBREV):
            merged[-1] += " " + part
        else:
            merged.append(part)
    return merged


class StreamChunker:
    """Accumulates streaming deltas; emits complete sentences when ready.

    A chunk is emitted when: it contains sentence-ending punctuation AND
    meets the minimum character threshold (short clauses sound choppy).
    """

    def __init__(self, min_chars: int = 40) -> None:
        self.min_chars = min_chars
        self._buffer = ""

    def feed(self, delta: str) -> List[str]:
        """Add a delta; return any complete sentence chunks."""
        self._buffer += delta
        chunks: List[str] = []

        while True:
            sentences = split_sentences(self._buffer)
            if len(sentences) < 2:
                # No complete sentence boundary yet — keep buffering unless
                # the buffer is getting long without punctuation.
                break
            candidate = sentences[0]
            if len(candidate) < self.min_chars and len(sentences) > 2:
                # Merge very short leading sentence with the next one
                merged = candidate + " " + sentences[1]
                rest = " ".join(sentences[2:])
                self._buffer = rest
                chunks.append(merged)
                continue
            if len(candidate) < self.min_chars:
                break
            rest = " ".join(sentences[1:])
            self._buffer = rest
            chunks.append(candidate)

        # Hard flush guard: buffer without punctuation but very long
        if len(self._buffer) > 300:
            chunks.append(self._buffer)
            self._buffer = ""
        return chunks

    def flush(self) -> str:
        """Return and clear whatever remains."""
        remaining = self._buffer.strip()
        self._buffer = ""
        return remaining
