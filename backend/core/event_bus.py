"""Typed event bus — the isolation layer between features.

Features NEVER import each other directly; they communicate through this bus.
A crash in one subscriber can never take down another feature.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List

log = logging.getLogger("hinata.bus")


@dataclass
class Event:
    name: str
    payload: Dict[str, Any] = field(default_factory=dict)
    source: str = ""


Handler = Callable[[Event], Any]


class EventBus:
    """Pub/sub with per-subscriber error isolation and async dispatch."""

    def __init__(self) -> None:
        self._handlers: Dict[str, List[Handler]] = {}
        self._wildcards: List[Handler] = []

    def subscribe(self, event_name: str, handler: Handler) -> None:
        self._handlers.setdefault(event_name, []).append(handler)

    def subscribe_all(self, handler: Handler) -> None:
        self._wildcards.append(handler)

    def emit(self, event_name: str, payload: Dict[str, Any] | None = None, source: str = "") -> Event:
        event = Event(name=event_name, payload=payload or {}, source=source)
        for handler in self._handlers.get(event_name, []) + self._wildcards:
            self._safe_call(handler, event)
        return event

    def _safe_call(self, handler: Handler, event: Event) -> None:
        try:
            result = handler(event)
            if hasattr(result, "__await__"):
                import asyncio
                asyncio.get_event_loop().create_task(result) if asyncio.iscoroutine(result) else None
        except Exception as exc:  # isolation: one bad subscriber never breaks others
            log.error("handler %r failed for %s: %s", handler, event.name, exc)


bus = EventBus()
