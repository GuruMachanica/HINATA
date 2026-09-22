"""HermesEngine — runs the vendored NousResearch AIAgent (or a direct fallback)."""
from __future__ import annotations

import json
import logging
import sys
import urllib.request
from typing import Optional

from ...core.config import (
    HERMES_DIR, MODEL_API_KEY, MODEL_ENDPOINT, MODEL_NAME,
)

log = logging.getLogger("hinata.hermes")


class HermesEngine:
    """Lazy-init wrapper around vendor/hermes-agent; falls back to raw chat."""

    def __init__(self) -> None:
        self._agent = None
        self._failed = False

    @property
    def available(self) -> bool:
        return self._ensure() is not None

    def _ensure(self):
        if self._agent is not None or self._failed:
            return self._agent
        if not HERMES_DIR.exists():
            log.warning("vendor/hermes-agent missing — fallback chat only")
            self._failed = True
            return None
        sys.path.insert(0, str(HERMES_DIR))
        try:
            import run_agent  # type: ignore  (vendored)
            self._agent = run_agent.AIAgent(
                provider="openai_compatible",
                model=MODEL_NAME,
                base_url=MODEL_ENDPOINT,
                api_key=MODEL_API_KEY,
                enabled_toolsets=[],
                quiet_mode=True, skip_memory=True, skip_background_review=True,
            )
            log.info("Hermes AIAgent ready (model=%s)", MODEL_NAME)
        except Exception as exc:
            log.warning("Hermes init failed (%s) — fallback chat", exc)
            self._failed = True
        return self._agent

    def chat(self, system: str, message: str) -> str:
        agent = self._ensure()
        if agent is not None:
            try:
                result = agent.run_conversation(message, system_message=system)
                if isinstance(result, dict):
                    return str(result.get("final_response") or "")
                return str(result or "")
            except Exception as exc:
                log.warning("agent turn failed (%s) — fallback", exc)
        return self._raw_chat(system, message)

    def _raw_chat(self, system: str, message: str) -> str:
        body = json.dumps({
            "model": MODEL_NAME,
            "messages": [{"role": "system", "content": system},
                          {"role": "user", "content": message}],
            "stream": False,
        }).encode()
        req = urllib.request.Request(
            f"{MODEL_ENDPOINT.rstrip('/')}/chat/completions",
            data=body, headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode())
                return data["choices"][0]["message"]["content"].strip()
        except Exception as exc:
            log.error("raw chat failed: %s", exc)
            return "My brain is offline — is Ollama running with hinata-brain?"
