"""
HINATA Event Dispatcher
Formats and streams decoupled JSON event frames to stdout / listeners.
"""

import json
from typing import Dict, Any

def dispatch_event(event_type: str, data: Dict[str, Any]) -> None:
    """Outputs a structured JSON event frame for downstream consumers."""
    frame = {
        "type": event_type,
        "payload": data
    }
    print(json.dumps(frame), flush=True)

def emit_state(state: str, **kwargs) -> None:
    """Helper to emit agent lifecycle states (thinking, speaking, idle)."""
    payload = {"state": state}
    payload.update(kwargs)
    dispatch_event("agent_state", payload)

def emit_tool_event(tool_name: str, status: str, result: Any = None) -> None:
    """Helper to emit tool call requests and results."""
    payload = {"tool": tool_name, "status": status}
    if result is not None:
        payload["result"] = result
    dispatch_event("tool_event", payload)
