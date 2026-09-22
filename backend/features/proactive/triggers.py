"""Proactive triggers — conditions that make HINATA speak up on her own."""
from __future__ import annotations

import random
import time
from abc import ABC, abstractmethod
from typing import Optional

from ...core.event_bus import EventBus

SEEDS = [
    "You have been quiet for a while. Say one short, warm check-in line to the user.",
    "It is a good moment for a small helpful tip about taking care of themselves or their machine. One sentence.",
    "Share one brief curious observation or question to invite conversation. One sentence.",
]


class Trigger(ABC):
    """A condition + a seed prompt for the brain."""

    name: str = "trigger"
    cooldown_s: int = 600

    def __init__(self, bus: EventBus) -> None:
        self.bus = bus
        self._last_fired = 0.0

    def ready(self) -> bool:
        return time.time() - self._last_fired >= self.cooldown_s

    def mark_fired(self) -> None:
        self._last_fired = time.time()

    @abstractmethod
    def evaluate(self) -> Optional[str]:
        """Return a seed prompt if this trigger wants to fire, else None."""


class IdleTrigger(Trigger):
    name = "idle"
    cooldown_s = 900

    def evaluate(self) -> Optional[str]:
        turns = self.bus.emit("memory.recent.query", {"limit": 1}).payload.get("turns") or []
        if not turns:
            return None
        last = turns[0]
        idle_for = time.time() - (last.get("created_at") or time.time())
        if idle_for > 1200 and random.random() < 0.4:
            return random.choice(SEEDS)
        return None


class SystemHealthTrigger(Trigger):
    name = "system_health"
    cooldown_s = 1800

    def evaluate(self) -> Optional[str]:
        from ...features.tools.registry import load_builtin_tools
        result = load_builtin_tools().dispatch("get_system_info", {})
        if result.ok and ("temperature" in result.output or "GB free" in result.output):
            low_disk = "free" in result.output and any(
                part.strip().startswith("Disk:") and part.split()[1].startswith("1")
                for part in result.output.splitlines()
            )
            hot = "8" in result.output  # crude: temperature with 80s
            if low_disk or hot:
                return ("System check shows the machine may be low on disk or running hot. "
                        "Tell the user in one short caring sentence.")
        return None


class NewSessionTrigger(Trigger):
    name = "new_session"
    cooldown_s = 3600

    def evaluate(self) -> Optional[str]:
        turns = self.bus.emit("memory.recent.query", {"limit": 2}).payload.get("turns") or []
        if not turns:
            return ("The user just started a fresh session. Greet them warmly in one "
                    "short line as HINATA.")
        return None
