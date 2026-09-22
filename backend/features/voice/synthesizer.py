"""TTSSynthesizer — edge-tts via subprocess, returns data-URI audio."""
from __future__ import annotations

import json
import logging
import subprocess
import sys
from typing import Optional

from ...core.config import NEURAL_TTS_PY

log = logging.getLogger("hinata.voice")


class TTSSynthesizer:
    def __init__(self, voice: str = "en-US-AriaNeural") -> None:
        self.voice = voice

    def synthesize(self, text: str) -> Optional[str]:
        """Returns 'data:audio/mp3;base64,...' or None on failure."""
        try:
            proc = subprocess.run(
                [sys.executable, str(NEURAL_TTS_PY), text],
                capture_output=True, text=True, timeout=60,
                encoding="utf-8", errors="replace",
            )
            if proc.returncode != 0:
                log.warning("tts subprocess failed: %s", proc.stderr[-200:])
                return None
            parsed = json.loads(proc.stdout.strip())
            return parsed.get("audio") if parsed.get("success") else None
        except Exception as exc:
            log.warning("tts error: %s", exc)
            return None
