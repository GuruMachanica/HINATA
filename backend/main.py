"""HINATA application entrypoint.

    uvicorn backend.main:app --port 8080      (dev)
    hinata-backend.exe                        (frozen product build)
"""
from __future__ import annotations

import logging

if __package__ in (None, ""):  # frozen exe: run as part of the backend package
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    __package__ = "backend"
    __import__("backend")

from .core.config import LOG_LEVEL, PROACTIVE_ENABLED
from .core.paths import BUNDLE_DIR
from .core.base_feature import get, setup_all
from .core.event_bus import bus
import os  # noqa: E402  (used by fast-engine env wiring)

from .core.logging_setup import install_crash_reporter, setup_logging  # noqa: E402
setup_logging(LOG_LEVEL)
install_crash_reporter()

# Bundled llama.cpp engine first: if present, it becomes the model endpoint
# (zero external dependencies). Falls back to Ollama automatically.
from .core.engine_bootstrap import EngineBootstrap, apply_engine_override  # noqa: E402
_bootstrap = EngineBootstrap()
apply_engine_override(_bootstrap.start())

# Optional fast chat model (tiny non-thinking GGUF on a second slot)
from .core.fast_engine import FastEngine, fast_endpoint  # noqa: E402
_fast = FastEngine()
_fast_url = _fast.start(_bootstrap.server_exe)
if _fast_url:
    os.environ["HINATA_FAST_ENDPOINT"] = _fast_url

# First-run provisioning: create hinata-omni from bundled GGUFs when missing
from .core.provision import FirstRunProvisioner  # noqa: E402
if BUNDLE_DIR is not None:  # only in the frozen product build
    FirstRunProvisioner().run()

# Import features -> each registers itself
from . import features  # noqa: E402,F401

setup_all()

# Proactive engine needs the running brain; wire after setup
from .features.brain import BrainFeature  # noqa: E402
from .features.proactive import ProactiveEngine  # noqa: E402
from .features.brain.warmup import warm_model  # noqa: E402

brain = get(BrainFeature.name)
proactive = ProactiveEngine(bus, brain.think)
warm_model()  # preload the Ollama model so first reply is fast

app = get("server").app


@app.on_event("startup")
async def _start_proactive() -> None:
    if PROACTIVE_ENABLED:
        proactive.start()


@app.on_event("shutdown")
async def _stop_proactive() -> None:
    proactive.stop()


if __name__ == "__main__":  # frozen exe entrypoint
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=int(os.getenv("HINATA_PORT", "8080")))
