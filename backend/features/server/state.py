"""ConnectionState — one live client; outbound JSON sending."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class ConnectionState:
    ws: Any
    state: str = "online"
    extra: Dict[str, Any] = field(default_factory=dict)

    async def send(self, event_type: str, payload: Dict[str, Any]) -> None:
        try:
            await self.ws.send_text(json.dumps({"type": event_type, "payload": payload}))
        except Exception:
            pass  # client gone; connection cleanup handled by the socket layer

    async def send_state(self, state: str) -> None:
        self.state = state
        await self.send("agent_state", {"state": state})
