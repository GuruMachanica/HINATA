"""
HINATA Audio Queue
Thread-safe queue with instant barge-in flushing for streaming TTS audio chunks.
Strictly under 60 LOC.
"""

import queue
from typing import Optional, Dict, Any

class AudioQueue:
    def __init__(self, maxsize: int = 50):
        self._q = queue.Queue(maxsize=maxsize)
        self.is_flushed = False

    def enqueue(self, item: Dict[str, Any]) -> bool:
        """Add sentence audio/directive to playback queue."""
        try:
            self._q.put_nowait(item)
            return True
        except queue.Full:
            return False

    def dequeue(self, timeout: float = 0.5) -> Optional[Dict[str, Any]]:
        """Retrieve next audio item; returns None on empty or timeout."""
        try:
            return self._q.get(timeout=timeout)
        except queue.Empty:
            return None

    def flush_barge_in(self) -> int:
        """Immediately drains all queued audio when user interrupts."""
        drained_count = 0
        while not self._q.empty():
            try:
                self._q.get_nowait()
                self._q.task_done()
                drained_count += 1
            except queue.Empty:
                break
        self.is_flushed = True
        return drained_count

    @property
    def is_empty(self) -> bool:
        return self._q.empty()
