"""VoiceFeature — isolated voice service over the bus."""
from __future__ import annotations

import base64
from typing import Optional

from ...core.base_feature import BaseFeature, register
from .synthesizer import TTSSynthesizer


@register
class VoiceFeature(BaseFeature):
    name = "voice"

    def __init__(self) -> None:
        super().__init__()
        self.synth = TTSSynthesizer()
        self._queue: list[str] = []

    def setup(self) -> None:
        self.bus.subscribe("voice.speak", self._on_speak)

    def _on_speak(self, event) -> None:
        text = event.payload.get("text", "").strip()
        if text:
            self._queue.append(text)

    def synthesize(self, text: str) -> Optional[str]:
        return self.synth.synthesize(text)

    def audio_bytes(self, text: str) -> Optional[bytes]:
        uri = self.synth.synthesize(text)
        if not uri:
            return None
        return base64.b64decode(uri.split(",", 1)[-1])
