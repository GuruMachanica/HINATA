"""CompletionClient — raw OpenAI-compatible chat calls to the local model.

Single responsibility: one HTTP completion with salvage. The engine adds
agent paths, retries and nudges on top of this.
"""
from __future__ import annotations

import json
import logging
import urllib.request

from ...core.config import MODEL_API_KEY, MODEL_NAME, THINK_BUDGET, model_endpoint
from .reply_salvage import salvage_reply

log = logging.getLogger("hinata.hermes")


class CompletionClient:
    def __init__(self, endpoint: str | None = None, model: str | None = None) -> None:
        # Optional per-client lane override (fast model vs omni)
        self._endpoint = endpoint
        self._model = model

    def complete(self, system: str, message: str, timeout: int = 120) -> tuple[str, str]:
        """Returns (salvaged_reply, raw_content). Raises on HTTP failure."""
        body = json.dumps({
            "model": self._model or MODEL_NAME,
            "messages": [{"role": "system", "content": system},
                          {"role": "user", "content": message}],
            "stream": False,
            # 64K ctx keeps Hermes happy; the cap bounds thinking time.
            # OpenAI-compat layer maps max_tokens onto Ollama num_predict.
            "max_tokens": THINK_BUDGET if not self._endpoint else 300,
        }).encode()
        req = urllib.request.Request(
            f"{(self._endpoint or model_endpoint()).rstrip('/')}/chat/completions",
            data=body,
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {MODEL_API_KEY}"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            msg = json.loads(resp.read().decode())["choices"][0]["message"]
        raw = msg.get("content") or ""
        thinking = msg.get("reasoning_content") or msg.get("reasoning") or msg.get("thinking") or ""
        return salvage_reply(raw, thinking), raw
