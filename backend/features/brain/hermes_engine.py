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
from .reply_salvage import clean_for_speech
from .turn_timeout import AGENT_TIMEOUT_S, with_timeout

log = logging.getLogger("hinata.hermes")

_NUDGE = "Answer immediately in one short sentence. No deliberation, no re-checking."


class HermesEngine:
    """Lazy-init wrapper around hermes-agent; falls back to raw chat."""

    def __init__(self) -> None:
        self._agent = None
        self._failed = False
        self._client = CompletionClient()

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
        """Single completion — the reliable hot path for the tool loop."""
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

    def chat_stream(self, system: str, message: str):
        """Yield text deltas as they arrive (SSE stream from Ollama)."""
        body = json.dumps({
            "model": MODEL_NAME,
            "messages": [{"role": "system", "content": system},
                          {"role": "user", "content": message}],
            "stream": True,
            "max_tokens": THINK_BUDGET,  # bound thinking time on streams too
        }).encode()
        req = urllib.request.Request(
            f"{model_endpoint().rstrip('/')}/chat/completions",
            data=body, headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                for raw_line in resp:
                    line = raw_line.decode("utf-8", errors="replace").strip()
                    if not line.startswith("data:"):
                        continue
                    payload = line[5:].strip()
                    if payload == "[DONE]":
                        break
                    try:
                        delta = json.loads(payload)["choices"][0]["delta"]
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue
                    piece = delta.get("content") or ""
                    if piece:
                        yield clean_for_speech(piece, preserve_edges=True)
        except Exception as exc:
            log.error("stream failed (%s) — falling back", exc)
            yield self.chat_raw(system, message)
