"""MoodFeature — persistent temperament: sets on replies, decays over time."""
from __future__ import annotations

from ...core.base_feature import BaseFeature, register
from .decay import MoodDecayEngine


@register
class MoodFeature(BaseFeature):
    name = "mood"

    def __init__(self) -> None:
        super().__init__()
        self.engine: MoodDecayEngine | None = None

    def setup(self) -> None:
        self.engine = MoodDecayEngine(self.bus.emit)
        self.engine.start()
        self.bus.subscribe("hinata.spoke", self._on_spoke)
        self.bus.subscribe("hinata.proactive", self._on_spoke)

    def teardown(self) -> None:
        if self.engine:
            self.engine.stop()

    def _on_spoke(self, event) -> None:
        mood = event.payload.get("mood")
        if mood:
            self.engine.set_mood(mood)

    def current(self) -> dict:
        return self.engine.current() if self.engine else {"mood": "neutral", "intensity": 0.0}
