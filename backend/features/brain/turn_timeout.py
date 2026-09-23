"""Hard timeout wrapper — one full agent turn can never hang the brain.

Uses a daemon worker + queue: on timeout the caller returns control
immediately (the daemon thread dies with the process, never joined).
"""
from __future__ import annotations

import queue
import threading

AGENT_TIMEOUT_S = 90  # ceiling on one full Hermes agent turn


def with_timeout(fn, seconds: float = AGENT_TIMEOUT_S, what: str = "turn"):
    """Run fn(); return its result or raise TimeoutError after `seconds`.

    Unlike a ThreadPoolExecutor context manager, this does NOT block on
    exit — the runaway worker is abandoned (daemon), not waited on.
    """
    result_q: queue.Queue = queue.Queue(maxsize=1)

    def _worker() -> None:
        try:
            result_q.put(("ok", fn()))
        except Exception as exc:  # noqa: BLE001 - forward anything
            result_q.put(("err", exc))

    threading.Thread(target=_worker, daemon=True, name=f"timeout:{what}").start()
    try:
        kind, value = result_q.get(timeout=seconds)
    except queue.Empty:
        raise TimeoutError(f"{what} exceeded {seconds:.0f}s") from None
    if kind == "err":
        raise value
    return value
