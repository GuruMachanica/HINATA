"""ProactiveEngine — background loop: evaluate triggers, think, emit speech."""
from __future__ import annotations

import asyncio
import random
from typing import Callable, List

from ...core.config import PROACTIVE_MIN_INTERVAL_S
from ...core.event_bus import EventBus
from .triggers import Trigger, IdleTrigger, SystemHealthTrigger, NewSessionTrigger


class ProactiveEngine:
    def __init__(self, bus: EventBus, brain_think: Callable[[str], dict]) -> None:
        self.bus = bus
        self.brain_think = brain_think
        self.triggers: List[Trigger] = [
            IdleTrigger(bus), SystemHealthTrigger(bus), NewSessionTrigger(bus),
        ]
        self._task: asyncio.Task | None = None
        self._running = False

    def start(self) -> None:
        self._running = True
        self._task = asyncio.get_event_loop().create_task(self._loop())

    def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()

    async def _loop(self) -> None:
        # settle before first proactivity
        await asyncio.sleep(PROACTIVE_MIN_INTERVAL_S)
        while self._running:
            try:
                await self._tick()
            except asyncio.CancelledError:
                break
            except Exception as exc:  # engine must never die
                self.bus.emit("proactive.error", {"error": str(exc)}, source="proactive")
                await asyncio.sleep(60)
            await asyncio.sleep(random.uniform(45, 90))

    async def _tick(self) -> None:
        for trigger in self.triggers:
            if not trigger.ready():
                continue
            seed = await asyncio.to_thread(trigger.evaluate)
            if not seed:
                continue
            trigger.mark_fired()
            result = await asyncio.to_thread(self.brain_think, seed)
            self.bus.emit("hinata.proactive", {
                "reply": result.get("reply", ""),
                "mood": result.get("mood", "calm"),
                "trigger": trigger.name,
                "seed": seed,
            }, source="proactive")
            break  # one initiative per tick
