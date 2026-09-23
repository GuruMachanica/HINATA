"""HINATA application entrypoint.

    uvicorn backend.main:app --port 8080
"""
from __future__ import annotations

import logging

from .core.config import LOG_LEVEL, PROACTIVE_ENABLED
from .core.base_feature import get, setup_all
from .core.event_bus import bus

logging.basicConfig(level=LOG_LEVEL, format="[%(levelname)s] %(name)s: %(message)s")

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
