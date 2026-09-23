"""Model warm-up — pings Ollama at startup so the brain never cold-starts."""
from __future__ import annotations

import json
import logging
import threading
import urllib.request

from ...core.config import MODEL_API_KEY, MODEL_NAME, model_endpoint

log = logging.getLogger("hinata.warmup")


def warm_model(async_: bool = True) -> None:
    """Load MODEL_NAME into VRAM/GPU (fire-and-forget by default)."""
    if async_:
        threading.Thread(target=_warm, daemon=True, name="hinata-warmup").start()
    else:
        _warm()


def _warm() -> None:
    body = json.dumps({
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": "warm up"}],
        "max_tokens": 1, "stream": False,
    }).encode()
    req = urllib.request.Request(
        f"{model_endpoint().rstrip('/')}/chat/completions",
        data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {MODEL_API_KEY}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120):
            log.info("model %s warmed and resident", MODEL_NAME)
    except Exception as exc:
        log.warning("warm-up failed (Ollama down?): %s", exc)
