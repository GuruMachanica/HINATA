"""ModelRouter — route each turn to the right model.

Fast lane (tiny non-thinking model): plain conversational turns — greetings,
chit-chat, short questions. Replies land in 1-3s instead of 15-50s.
Omni lane (thinking multimodal): anything needing reasoning, tools, memory
recall, or vision. Detection is deliberately cheap: keyword + heuristics,
no extra model call.
"""
from __future__ import annotations

import logging
import os
import re

log = logging.getLogger("hinata.router")

# Turn shapes that need the big model even without obvious tool intent
_COMPLEX = re.compile(
    r"\b(remember|recall|what did i|my name|my favorite|search|look at|screen|"
    r"open|launch|run|calculate|weather|news|time|date|battery|system)\b", re.I)
_QUESTION = re.compile(r"\?\s*$")
# Cheap small talk the 0.5B handles perfectly
_SIMPLE = re.compile(
    r"^(hi|hey|hello|yo|sup|good (morning|evening|night)|thanks|thank you|"
    r"ok|okay|nice|cool|lol|haha|bye|goodbye|how are you|what's up|whats up)"
    r"[\s!.,]*$", re.I)


class ModelRouter:
    """Stateless per-turn model choice."""

    def __init__(self) -> None:
        self._fast_url: str | None = None

    def wire(self) -> None:
        self._fast_url = os.getenv("HINATA_FAST_ENDPOINT", "").rstrip("/") or None
        if self._fast_url:
            log.info("router: fast lane on %s", self._fast_url)
        else:
            log.info("router: single-lane (omni only)")

    @property
    def fast_available(self) -> bool:
        return bool(self._fast_url)

    def wants_fast(self, query: str) -> bool:
        """True when this turn is simple enough for the fast model."""
        if not self._fast_url or not query.strip():
            return False
        if _SIMPLE.match(query.strip()):
            return True
        if _COMPLEX.search(query) or _QUESTION.search(query):
            return False
        return len(query.split()) <= 12  # short statements = chit-chat
