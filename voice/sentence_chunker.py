"""
HINATA Sentence Chunker
Splits streaming LLM tokens into complete sentences for low-latency TTS dispatch.
"""

import re
from typing import Generator, List

SENTENCE_SPLIT_REGEX = re.compile(r'(?<=[.!?])\s+')

def split_into_sentences(text: str) -> List[str]:
    """Splits full text block into cleaned sentences for TTS."""
    clean = text.strip().replace("\r\n", " ").replace("\n", " ")
    parts = SENTENCE_SPLIT_REGEX.split(clean)
    return [p.strip() for p in parts if p.strip()]

def stream_sentences(token_stream: Generator[str, None, None]) -> Generator[str, None, None]:
    """Yields complete sentences as tokens arrive from streaming LLM output."""
    buffer = ""
    for token in token_stream:
        buffer += token
        if any(punct in token for punct in [".", "!", "?"]):
            parts = SENTENCE_SPLIT_REGEX.split(buffer)
            if len(parts) > 1:
                yield parts[0].strip()
                buffer = " ".join(parts[1:])
    if buffer.strip():
        yield buffer.strip()
