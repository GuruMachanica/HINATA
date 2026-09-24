"""FastEngine — tiny non-thinking chat model on a second llama-server slot.

Plain chat turns route here for ~1-3s responses; the big omni model keeps
tools, vision, memory, and anything requiring reasoning. Optional: when the
fast GGUF is absent (or VRAM-constrained) everything falls back to omni.
"""
from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

from .config import model_endpoint
from .engine_process import engine_health, launch, wait_healthy
from .paths import BUNDLE_DIR

log = logging.getLogger("hinata.fastengine")

FAST_PORT = int(os.getenv("HINATA_FAST_PORT", "8198"))
FAST_URL = f"http://127.0.0.1:{FAST_PORT}"
FAST_HEALTH_S = 60


def fast_gguf() -> Path:
    return BUNDLE_DIR / "models_ollama" / "hinata-fast-q4km.gguf"


class FastEngine:
    """Owns the optional small-model server process."""

    def __init__(self) -> None:
        self.proc: subprocess.Popen | None = None

    def start(self, server_exe: Path | None) -> str | None:
        """Return an OpenAI-compatible base URL, or None when unavailable."""
        if engine_health(FAST_URL):
            log.info("fast engine: reusing llama-server on :%d", FAST_PORT)
            return FAST_URL + "/v1"
        gguf = fast_gguf()
        if not server_exe or not gguf.exists():
            log.info("fast engine: not bundled — all turns use omni")
            return None
        self.proc = launch(server_exe, gguf, None, FAST_PORT, fast=True)
        if wait_healthy(FAST_URL, FAST_HEALTH_S):
            log.info("fast engine: hinata-fast loaded (instant chat turns)")
            return FAST_URL + "/v1"
        log.warning("fast engine: failed to start — falling back to omni")
        self.stop()
        return None

    def stop(self) -> None:
        from .engine_process import stop as _stop
        _stop(self.proc)
        self.proc = None


def fast_endpoint() -> str | None:
    """Configured fast-model endpoint, or None to route everything to omni."""
    url = os.getenv("HINATA_FAST_ENDPOINT", "")
    return url.rstrip("/") or None


def omni_fallback_url() -> str:
    return model_endpoint()
