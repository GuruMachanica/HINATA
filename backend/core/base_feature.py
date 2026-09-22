"""Feature base class + registry — every capability is a self-contained plugin."""
from __future__ import annotations

import logging
from abc import ABC
from typing import Dict, Type

from .event_bus import EventBus, bus as default_bus


class BaseFeature(ABC):
    """A feature owns its storage, subscribes to events, emits its own.

    Lifecycle: __init__(bus) -> setup() -> [running] -> teardown().
    Features never import each other — only the bus and core.
    """

    name: str = "feature"

    def __init__(self, bus: EventBus = default_bus) -> None:
        self.bus = bus
        self.log = logging.getLogger(f"hinata.{self.name}")

    def setup(self) -> None:
        """Create tables, register handlers, start workers."""

    def teardown(self) -> None:
        """Release resources."""


_registry: Dict[str, BaseFeature] = {}


def register(feature_cls: Type[BaseFeature]) -> Type[BaseFeature]:
    """Class decorator: @register class BrainFeature(BaseFeature)..."""
    _registry[feature_cls.name] = feature_cls()
    return feature_cls


def get(name: str) -> BaseFeature:
    return _registry[name]


def setup_all() -> None:
    for instance in _registry.values():
        instance.setup()
        instance.log.info("ready")


def teardown_all() -> None:
    for instance in _registry.values():
        instance.teardown()
