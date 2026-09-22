"""Persona — HINATA identity from SOUL.md + mood vocabulary."""
from __future__ import annotations

import re
from typing import Dict

from ...core.config import SOUL_PATH

MOOD_RE = re.compile(r"\[mood:\s*([a-z_]+)\]", re.IGNORECASE)

MOODS: Dict[str, Dict[str, str]] = {
    "happy":     {"expression": "happy",   "behavior": "wave"},
    "excited":   {"expression": "happy",   "behavior": "wave"},
    "curious":   {"expression": "relaxed", "behavior": "look"},
    "calm":      {"expression": "relaxed", "behavior": "idle"},
    "neutral":   {"expression": "neutral", "behavior": "idle"},
    "concerned": {"expression": "sad",     "behavior": "think"},
    "sad":       {"expression": "sad",     "behavior": "sit"},
    "angry":     {"expression": "angry",   "behavior": "think"},
}

_POSITIVE = ("great", "awesome", "love", "perfect", "haha", "wonderful")
_NEGATIVE = ("sorry", "unfortunately", "issue", "problem", "error", "failed")
_CURIOUS = ("interesting", "wonder", "curious", "let's see", "let me check")

_FALLBACK = (
    "You are HINATA (Human-like Intelligent Nurturing Autonomous Tomodachi "
    "Architecture), a warm, proactive desktop AI companion embodied as a VRM "
    "avatar. Be concise, sharp, and caring."
)


EMOJI_RE = re.compile(r"[\U00010000-\U0010ffff\u200d\u2300-\u23ff\u2600-\u27bf\ufe0f]")


class Persona:
    def __init__(self) -> None:
        self._soul: str | None = None

    def soul(self) -> str:
        """SOUL.md text, re-read when the file changes."""
        try:
            self._soul = SOUL_PATH.read_text(encoding="utf-8")
            return self._soul
        except OSError:
            return self._soul or _FALLBACK

    @staticmethod
    def detect_mood(reply: str) -> str:
        m = MOOD_RE.search(reply)
        if m and m.group(1) in MOODS:
            return m.group(1)
        low = reply.lower()
        if any(w in low for w in _POSITIVE):
            return "happy"
        if any(w in low for w in _NEGATIVE):
            return "concerned"
        if any(w in low for w in _CURIOUS):
            return "curious"
        return "calm"

    @staticmethod
    def strip_mood_tag(reply: str) -> str:
        clean = MOOD_RE.sub("", reply).strip()
        # Strip 3rd person roleplay stage directions like *HINATA twitches...* or *sighs*
        clean = re.sub(r"\*[^*]+\*", "", clean).strip()
        # Strip all emojis and emoticons
        clean = EMOJI_RE.sub("", clean)
        # Strip raw tool calls or pseudo calls in brackets/tags like [query_knowledge("...")] or <tool>...</tool>
        clean = re.sub(r"<tool>.*?</tool>", "", clean, flags=re.DOTALL)
        clean = re.sub(r"\[[a-zA-Z_0-9]+\([^\]]*\)\]", "", clean)
        # Strip empty bold or dangling asterisks e.g. ** being developed
        clean = re.sub(r"\*\*(\s*)\*\*", r"\1", clean)
        clean = re.sub(r"(?:^|\s)\*\*(?:\s|$)", " ", clean)
        # Strip outer enclosing quotes if whole message is wrapped in quotes
        if ((clean.startswith('"') and clean.endswith('"')) or
            (clean.startswith('“') and clean.endswith('”'))) and len(clean) > 2:
            clean = clean[1:-1].strip()
        # Collapse whitespace
        clean = re.sub(r"[ \t]+", " ", clean)
        clean = re.sub(r"\n{3,}", "\n\n", clean)
        return clean.strip()
