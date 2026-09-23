"""MoodDecayEngine — her mood is a persistent state, not a per-reply flash.

Current mood decays toward neutral over minutes; strong moods linger longer.
Emits `avatar_mood` updates whenever the baseline shifts, so the avatar's
expression stays coherent even between conversations.
"""
from __future__ import annotations

import threading
import time
from typing import Dict, Optional

DECAY_HALF_LIFE_S = 180.0        # mood strength halves every 3 minutes
TICK_S = 15.0                    # check cadence
INTENSITY: Dict[str, float] = {  # peak intensity per mood
    "happy": 0.8, "excited": 1.0, "curious": 0.6, "calm": 0.4,
    "neutral": 0.0, "concerned": 0.7, "sad": 0.9, "angry": 1.0,
}


class MoodDecayEngine:
    def __init__(self, emit) -> None:
        """emit(name, payload, source) — usually bus.emit."""
        self._emit = emit
        self._mood = "neutral"
        self._intensity = 0.0
        self._set_at = time.time()
        self._lock = threading.Lock()
        self._timer: Optional[threading.Timer] = None
        self._running = False

    # ---- lifecycle -------------------------------------------------
    def start(self) -> None:
        self._running = True
        self._schedule()

    def stop(self) -> None:
        self._running = False
        if self._timer:
            self._timer.cancel()

    def _schedule(self) -> None:
        if not self._running:
            return
        self._timer = threading.Timer(TICK_S, self._tick)
        self._timer.daemon = True
        self._timer.start()

    # ---- API -------------------------------------------------------
    def set_mood(self, mood: str) -> Dict:
        """Called after every reply; records mood + intensity snapshot."""
        with self._lock:
            self._mood = mood if mood in INTENSITY else "neutral"
            self._intensity = INTENSITY.get(self._mood, 0.0)
            self._set_at = time.time()
            return self.snapshot()

    def current(self) -> Dict:
        with self._lock:
            return self.snapshot()

    def snapshot(self) -> Dict:
        elapsed = time.time() - self._set_at
        decayed = self._intensity * (0.5 ** (elapsed / DECAY_HALF_LIFE_S))
        if decayed < 0.05:
            return {"mood": "neutral", "intensity": 0.0}
        return {"mood": self._mood, "intensity": round(decayed, 3)}

    # ---- internal --------------------------------------------------
    def _tick(self) -> None:
        try:
            snap = self.current()
            if snap["mood"] != "neutral" and snap["intensity"] < 0.05:
                with self._lock:
                    self._mood, self._intensity = "neutral", 0.0
                self._emit("avatar_mood", {
                    "mood": "neutral", "expression": "neutral", "behavior": None,
                }, source="mood")
        except Exception:
            pass  # mood decay must never crash
        finally:
            self._schedule()
