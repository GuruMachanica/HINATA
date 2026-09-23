"""EngineBootstrap — launch the llama.cpp server bundled inside the exe.

The frozen exe carries llama-server.exe (Vulkan) + the hinata-omni GGUFs.
On boot this starts the engine on a private port and points the brain's
MODEL_ENDPOINT at it — zero external dependencies. If an engine is already
listening on that port, it is reused. Ollama remains a fallback backend.
"""
from __future__ import annotations

import logging
import os
import subprocess  # noqa: F401  (re-exported type)
import sys
from pathlib import Path

from .config import MODEL_ENDPOINT
from .engine_process import engine_health, extract_engine, launch, stop, wait_healthy
from .paths import BUNDLE_DIR

log = logging.getLogger("hinata.engine")

ENGINE_PORT = int(os.getenv("HINATA_ENGINE_PORT", "8199"))
ENGINE_URL = f"http://127.0.0.1:{ENGINE_PORT}"
HEALTH_TIMEOUT_S = 180


class EngineBootstrap:
    """Start (or reuse) the bundled llama.cpp server; expose its endpoint."""

    def __init__(self) -> None:
        self.server_exe: Path | None = extract_engine()
        self.model_gguf = BUNDLE_DIR / "models_ollama" / "hinata-omni-q4km.gguf"
        self.mmproj_gguf = BUNDLE_DIR / "models_ollama" / "hinata-omni-mmproj.gguf"
        self.proc: subprocess.Popen | None = None

    def start(self) -> str | None:
        """Return the OpenAI-compatible base URL to use, or None to keep default."""
        if engine_health(ENGINE_URL):
            log.info("engine: reusing running llama-server on :%d", ENGINE_PORT)
            return ENGINE_URL + "/v1"
        if not self.server_exe or not self.model_gguf.exists():
            log.info("engine: no bundled engine — using configured endpoint %s",
                     MODEL_ENDPOINT)
            return None
        self.proc = launch(self.server_exe, self.model_gguf, self.mmproj_gguf,
                           ENGINE_PORT)
        if wait_healthy(ENGINE_URL, HEALTH_TIMEOUT_S):
            log.info("engine: hinata-omni loaded (GPU offload, multimodal)")
            return ENGINE_URL + "/v1"
        log.warning("engine: not healthy in %.0fs — falling back to Ollama",
                    HEALTH_TIMEOUT_S)
        self.stop()
        return None

    def stop(self) -> None:
        stop(self.proc)
        self.proc = None


def apply_engine_override(url: str | None) -> None:
    """Point the brain's config at the bundled engine before features load."""
    if url:
        os.environ["HINATA_MODEL_ENDPOINT"] = url
        log.info("engine: MODEL_ENDPOINT -> %s", url)


def is_frozen_product() -> bool:
    return bool(getattr(sys, "frozen", False)) and (BUNDLE_DIR / "engine").exists()
