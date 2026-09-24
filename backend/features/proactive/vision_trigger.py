"""SceneVisionTrigger — she glances at the screen on her own initiative.

Occasionally (long idle, fair odds) captures the screen, asks the omni
vision model what the user is up to, and speaks one short observation —
like a friend glancing over your shoulder. Heavily rate-limited and
gated on a privacy env flag.
"""
from __future__ import annotations

import os
import random
import time
from typing import Optional

from ...core.event_bus import EventBus
from .triggers import Trigger

SEED_VISION = (
    "You just glanced at the user's screen and saw: {scene}. "
    "Comment in one short, warm, non-intrusive line. Never mention you "
    "took a screenshot; speak as a friend noticing what they are doing."
)


class SceneVisionTrigger(Trigger):
    name = "scene_vision"
    cooldown_s = 2700  # at most ~once per 45 min

    def __init__(self, bus: EventBus) -> None:
        super().__init__(bus)
        self.enabled = os.getenv("HINATA_PROACTIVE_VISION", "1") == "1"

    def evaluate(self) -> Optional[str]:
        if not self.enabled or random.random() > 0.5:
            return None
        # Only glance when the user has been away from conversation a while
        turns = self.bus.emit("memory.recent.query", {"limit": 1}).payload.get("turns") or []
        if not turns:
            return None
        idle_for = time.time() - (turns[0].get("created_at") or time.time())
        if idle_for < 900:
            return None
        try:
            from ...features.tools.builtin.vision_tools import ask_vlm, _grab_screen_jpeg_b64
            jpeg = _grab_screen_jpeg_b64()
            if not jpeg:
                return None
            scene = ask_vlm(
                "In one short sentence, what is the user working on right now? "
                "Be concrete (app, activity, topic). No sensitive details.",
                jpeg,
            )
        except Exception:
            return None
        if not scene or len(scene) > 300:
            return None
        return SEED_VISION.format(scene=scene)
