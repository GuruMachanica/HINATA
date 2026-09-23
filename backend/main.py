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

logging.basicConfig(level=LOG_LEVEL, format="[%(levelname)s] %(name)s: %(message)s")

# Bundled llama.cpp engine first: if present, it becomes the model endpoint
# (zero external dependencies). Falls back to Ollama automatically.
from .core.engine_bootstrap import EngineBootstrap, apply_engine_override  # noqa: E402
apply_engine_override(EngineBootstrap().start())

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
