"""FirstRunProvisioner — makes the frozen exe self-provisioning.

On boot, if Ollama is running but `hinata-omni` is missing (fresh machine),
creates it from the GGUFs bundled inside the exe. Also ensures the
nomic-embed-text RAG model is present. Idempotent: every check is a no-op
when the requirement is already satisfied.
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import sys
import urllib.request
from pathlib import Path

from .config import model_endpoint

log = logging.getLogger("hinata.provision")

MODEL_NAME = "hinata-omni"
EMBED_MODEL = "nomic-embed-text"
CREATE_TIMEOUT_S = 900

_MODELFILE = """FROM {gguf}
FROM {mmproj}
RENDERER qwen3-vl-thinking
PARSER qwen3-vl-thinking
PARAMETER temperature 0.5
PARAMETER top_k 20
PARAMETER top_p 0.95
PARAMETER repeat_penalty 1.2
PARAMETER presence_penalty 1.5
PARAMETER num_predict 2048
PARAMETER num_ctx 65536
SYSTEM \"\"\"You are HINATA (Human-like Intelligent Nurturing Autonomous
Tomodachi Architecture), an intelligent, proactive AI companion embodied as a
3D VRM avatar on the user's desktop. Be concise, warm, and technically sharp.
Keep your reasoning short, then always give your final answer after </think>.
When appropriate, prepend a mood tag like [mood: happy|curious|concerned|calm|
neutral|excited] to your reply.\"\"\"
"""


def _api(path: str, payload: dict | None = None, timeout: int = 10):
    url = model_endpoint().replace("/v1", "") + path
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method="POST" if data else "GET")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


class FirstRunProvisioner:
    """Ensures the Ollama models HINATA needs exist on this machine."""

    def __init__(self) -> None:
        meipass = Path(getattr(sys, "_MEIPASS", "."))
        self.bundled_gguf = meipass / "models_ollama" / "hinata-omni-q4km.gguf"
        self.bundled_mmproj = meipass / "models_ollama" / "hinata-omni-mmproj.gguf"

    def ollama_up(self) -> bool:
        try:
            _api("/api/tags")
            return True
        except Exception:
            return False

    def model_exists(self, name: str) -> bool:
        try:
            tags = _api("/api/tags").get("models", [])
            return any(m.get("name", "").startswith(name) for m in tags)
        except Exception:
            return False

    def ensure_model(self) -> bool:
        """Create hinata-omni from bundled GGUFs. True when model is ready."""
        if self.model_exists(MODEL_NAME):
            return True
        if not self.bundled_gguf.exists():
            log.warning("provision: %s missing and no bundled GGUF", MODEL_NAME)
            return False
        workdir = Path(os.getenv("LOCALAPPDATA", ".")) / "HINATA" / "models"
        workdir.mkdir(parents=True, exist_ok=True)
        gguf = workdir / self.bundled_gguf.name
        mmproj = workdir / self.bundled_mmproj.name
        if not gguf.exists():
            log.info("provision: extracting model (%.1f GB)...",
                     self.bundled_gguf.stat().st_size / 1e9)
            shutil.copyfile(self.bundled_gguf, gguf)
            shutil.copyfile(self.bundled_mmproj, mmproj)
        log.info("provision: creating %s in Ollama (one-time, ~1 min)...", MODEL_NAME)
        _api("/api/create", {"model": MODEL_NAME,
                             "modelfile": _MODELFILE.format(gguf=gguf, mmproj=mmproj),
                             "stream": False}, timeout=CREATE_TIMEOUT_S)
        log.info("provision: %s ready", MODEL_NAME)
        return True

    def ensure_embed_model(self) -> bool:
        if self.model_exists(EMBED_MODEL):
            return True
        log.info("provision: pulling %s (RAG embeddings, 274 MB)...", EMBED_MODEL)
        try:
            _api("/api/pull", {"model": EMBED_MODEL, "stream": False}, timeout=600)
            return True
        except Exception as exc:
            log.warning("provision: embed pull failed: %s", exc)
            return False

    def run(self) -> None:
        if not self.ollama_up():
            log.warning("provision: Ollama not reachable — start Ollama, then "
                        "relaunch HINATA. Download: https://ollama.com")
            return
        self.ensure_model()
        self.ensure_embed_model()
