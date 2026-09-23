"""Reply salvage — extract a usable answer from any model reply shape.

Handles thinking models whose reasoning overruns the token budget: falls
back to the 'thinking'/'reasoning_content' field, strips think tags, and
removes emojis so speech and the text bubble stay clean.
"""
from __future__ import annotations

import re

EMOJI_RE = re.compile(
    "["
    "\U0001F000-\U0001FAFF"
    "\u2600-\u27BF"
    "\u2190-\u21FF\u2300-\u23FF\u2460-\u24FF\u25A0-\u25FF\u2900-\u297F"
    "\uFE00-\uFE0F\u200D\u20E3\u20E0]"
)
STAGE_DIRECTION_RE = re.compile(r"\*[^*\n]{1,80}\*")
MOOD_TAG_RE = re.compile(r"\s*\[mood:\s*[a-z_]+\]\s*", re.IGNORECASE)


CONCLUSION_MARKERS = ("final answer", "the answer is", "i will answer", "my reply")

# Meta-language that marks a tail as planning-talk, not an answer.
_META_WORDS = ("should", "mention", "respond", "user asked", "perhaps", "maybe",
               "need to", "let me", "check", "format", "according", "settings",
               "call ", "tool", "()", "json", "mood tag")


def salvage_reply(content: str, thinking: str = "") -> str:
    """Return the best answer text from a chat message.

    Thinking text is ONLY used when it contains an explicit conclusion —
    surfacing raw deliberation reads as broken, so overrun falls back to
    empty and the caller retries with a nudge.
    """
    text = (content or "").strip()
    if not text:
        text = conclusion_from_thinking(thinking)
    if "</think>" in text:
        text = text.split("</think>", 1)[1]
    return clean_for_speech(text)


def conclusion_from_thinking(thinking: str) -> str:
    """Extract the stated conclusion from overrun reasoning, else empty."""
    low = (thinking or "").lower()
    for marker in CONCLUSION_MARKERS:
        idx = low.rfind(marker)
        if idx == -1:
            continue
        tail = thinking[idx + len(marker):].strip(" :\n-*\"")
        tail = tail.split("\n")[0].strip(" .*")
        low_tail = tail.lower()
        if len(tail) > 10 and not any(w in low_tail for w in _META_WORDS):
            return tail
    return ""


def clean_for_speech(text: str) -> str:
    """Strip emojis, mood tags, stage directions, dangling markdown."""
    out = MOOD_TAG_RE.sub(" ", text or "")
    out = EMOJI_RE.sub("", out)
    out = STAGE_DIRECTION_RE.sub("", out)
    out = re.sub(r"<think>.*?</think>", "", out, flags=re.DOTALL)
    out = re.sub(r"[ \t]{2,}", " ", out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()
