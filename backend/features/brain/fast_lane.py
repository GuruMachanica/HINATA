"""FastLane — the tiny-model chat lane (extracted from hermes_engine)."""
from __future__ import annotations

import logging

from ...core.fast_engine import fast_endpoint
from .completion_client import CompletionClient
from .model_router import ModelRouter

log = logging.getLogger("hinata.hermes")


class FastLane:
    """Owns the optional fast-model client + routing decision."""

    def __init__(self) -> None:
        self.router = ModelRouter()
        self.client: CompletionClient | None = None

    def wire(self) -> None:
        """Pick up the fast-engine endpoint (call once at feature setup)."""
        url = fast_endpoint()
        if url:
            self.client = CompletionClient(endpoint=url, model="hinata-fast")
            self.router.wire()

    def maybe_reply(self, system: str, message: str,
                    timeout: int = 30) -> str | None:
        """Return a fast reply when the turn qualifies, else None."""
        if not self.client or not self.router.wants_fast(message):
            return None
        try:
            reply, _ = self.client.complete(system, message, timeout=timeout)
            if reply:
                return reply
        except Exception as exc:
            log.warning("fast lane failed (%s) — omni takes over", exc)
        return None


def make_fast_lane() -> FastLane:
    return FastLane()
