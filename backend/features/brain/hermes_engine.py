"""HermesEngine — vendored NousResearch AIAgent + direct completion fallback.

Hot path: the tool loop calls chat_raw() (single completion, most reliable).
Full agent power stays available via chat() with a hard timeout.
"""
from __future__ import annotations

import json
import logging
import sys
import urllib.request

from ...core.config import (HERMES_DIR, MODEL_API_KEY, MODEL_NAME, THINK_BUDGET,
                            model_endpoint)
from .completion_client import CompletionClient
from .fast_lane import make_fast_lane
from .omni_stream import stream_omni
from .turn_timeout import AGENT_TIMEOUT_S, with_timeout

log = logging.getLogger("hinata.hermes")

_NUDGE = "Answer immediately in one short sentence. No deliberation, no re-checking."


class HermesEngine:
    """Lazy-init wrapper around hermes-agent; falls back to raw chat."""

    def __init__(self) -> None:
        self._agent = None
        self._failed = False
        self._client = CompletionClient()
        self._fast: make_fast_lane | None = None

    @property
    def available(self) -> bool:
        return self._ensure() is not None

    def _ensure(self):
        if self._agent is not None or self._failed:
            return self._agent
        if not HERMES_DIR.exists():
            log.warning("hermes-agent missing — fallback chat only")
            self._failed = True
            return None
        sys.path.insert(0, str(HERMES_DIR))
        try:
            import run_agent  # type: ignore  (vendored)
            self._agent = run_agent.AIAgent(
                provider="openai_compatible",
                model=MODEL_NAME,
                base_url=model_endpoint(),
                api_key=MODEL_API_KEY,
                enabled_toolsets=[],
                quiet_mode=True, skip_memory=True, skip_background_review=True,
            )
            log.info("Hermes AIAgent ready (model=%s)", MODEL_NAME)
        except Exception as exc:
            log.warning("Hermes init failed (%s) — fallback chat", exc)
            self._failed = True
        return self._agent

    def chat_raw(self, system: str, message: str) -> str:
        """Fast lane first, then omni single completion (tool loop hot path)."""
        fast = self._fast.maybe_reply(system, message) if self._fast else None
        if fast:
            return fast
        try:
            reply, _ = self._client.complete(system, message)
            if reply:
                return reply
        except Exception as exc:
            log.error("raw chat failed: %s", exc)
            return "My brain is offline — is Ollama running with hinata-omni?"
        # Thinking overran the cap: one nudge usually lands a clean stop.
        try:
            reply, _ = self._client.complete(system, f"{message}\n\n({_NUDGE})")
            return reply or "Hmm, my thoughts drifted off. Ask me again?"
        except Exception as exc:
            log.error("nudge chat failed: %s", exc)
            return "I lost that thought somewhere — ask me again?"

    def chat(self, system: str, message: str) -> str:
        """Full Hermes agent turn (toolsets, continuations) with hard timeout."""
        agent = self._ensure()
        if agent is not None:
            try:
                result = with_timeout(
                    lambda: agent.run_conversation(message, system_message=system),
                    AGENT_TIMEOUT_S, "hermes agent turn")
                if isinstance(result, dict):
                    return str(result.get("final_response") or "")
                return str(result or "")
            except Exception as exc:
                log.warning("agent turn failed (%s) — fallback", exc)
        return self.chat_raw(system, message)

    def wire_router(self) -> None:
        """Called at feature setup: activate the fast lane if bundled."""
        self._fast = make_fast_lane()
        self._fast.wire()

    def chat_stream(self, system: str, message: str):
        """Yield text deltas; simple turns take the fast lane first."""
        fast = self._fast.maybe_reply(system, message) if self._fast else None
        if fast:
            yield fast
            return
        yield from self._stream_omni(system, message)

    def _stream_omni(self, system: str, message: str):
        got_any = False
        for piece in stream_omni(system, message):
            got_any = True
            yield piece
        if not got_any:  # stream died or thought overruns — nudge fallback
            yield self.chat_raw(system, f"{message}\n\n({_NUDGE})")
