"""OmniStream — SSE streaming from the omni model (split from hermes_engine)."""
from __future__ import annotations

import json
import logging
import urllib.request

from ...core.config import MODEL_NAME, THINK_BUDGET, model_endpoint
from .reply_salvage import clean_for_speech

log = logging.getLogger("hinata.hermes")


def stream_omni(system: str, message: str):
    """Yield clean text deltas from omni's OpenAI-compatible stream."""
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
        return None  # caller decides fallback
