"""TTSSynthesizer — edge-tts via subprocess, returns data-URI audio with LRU cache."""
from __future__ import annotations

import collections
import json
import logging
import subprocess
import sys
import threading
from typing import Optional

from ...core.config import NEURAL_TTS_PY

log = logging.getLogger("hinata.voice")

MAX_TTS_TEXT_LEN = 500
CACHE_CAPACITY = 64


class TTSSynthesizer:
    def __init__(self, voice: str = "en-US-AriaNeural") -> None:
        self.voice = voice
        self._cache: collections.OrderedDict[str, str] = collections.OrderedDict()
        self._lock = threading.Lock()

    def synthesize(self, text: str) -> Optional[str]:
        """Returns 'data:audio/mp3;base64,...' or None on failure."""
        clean = (text or "").strip()
        if not clean:
            return None

        # Truncate to reasonable max length to prevent CPU/memory abuse
        if len(clean) > MAX_TTS_TEXT_LEN:
            clean = clean[:MAX_TTS_TEXT_LEN].rsplit(" ", 1)[0] + "..."

        with self._lock:
            if clean in self._cache:
                self._cache.move_to_end(clean)
                return self._cache[clean]

        try:
            proc = subprocess.run(
                [sys.executable, str(NEURAL_TTS_PY), clean],
                capture_output=True, text=True, timeout=30,
                encoding="utf-8", errors="replace",
            )
            if proc.returncode != 0:
                log.warning("tts subprocess failed: %s", proc.stderr[-200:])
                return None
            parsed = json.loads(proc.stdout.strip())
            audio_uri = parsed.get("audio") if parsed.get("success") else None

            if audio_uri:
                with self._lock:
                    self._cache[clean] = audio_uri
                    if len(self._cache) > CACHE_CAPACITY:
                        self._cache.popitem(last=False)
            return audio_uri

        except Exception as exc:
            log.warning("tts error: %s", exc)
            return None
