"""
HINATA Agent Bridge
Coordinator orchestrating prompt queries, tool dispatch, and event streaming.
Strictly decoupled and modular.
"""

import os
import sys
import json
import argparse
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "hermes-core"))
sys.path.insert(0, str(ROOT_DIR / "hermes-core" / "tools"))

from env_loader import load_env_file
from event_dispatcher import dispatch_event, emit_state, emit_tool_event
from model_client import call_local_chat

try:
    from system_stats import get_system_snapshot
except ImportError:
    get_system_snapshot = None

load_env_file(ROOT_DIR / ".env")
DEFAULT_ENDPOINT = os.getenv("HERMES_MODEL_ENDPOINT", "http://127.0.0.1:11434/v1")
DEFAULT_MODEL = os.getenv("HERMES_MODEL_NAME", "dolphin3")

def run_query(prompt: str, context: str = "", model: str = DEFAULT_MODEL, endpoint: str = DEFAULT_ENDPOINT) -> str:
    """Executes a query, dynamically injecting tool data and avatar context."""
    emit_state("thinking", model=model)
    system_context = ""
    lower = prompt.lower()
    
    if any(k in lower for k in ["gpu", "vram", "ram", "specs", "hardware", "stats"]):
        emit_tool_event("system_stats", "executing")
        if get_system_snapshot:
            stats = get_system_snapshot()
            emit_tool_event("system_stats", "completed", result=stats)
            system_context = f"\n[Telemetry]:\n{json.dumps(stats, indent=2)}\n"

    soul_path = ROOT_DIR / "hermes-core" / "config" / "SOUL.md"
    if soul_path.exists():
        sys_prompt = soul_path.read_text(encoding="utf-8")
    else:
        sys_prompt = (
            "You are HINATA, an intelligent AI companion embodied as a VRM avatar in 3D. "
            "You are fully aware of your physical avatar, demonic horns, and current wardrobe attire. "
            "Accurately reflect what you are wearing (or if you are unclad with zero outerwear) when asked."
        )
    if context:
        sys_prompt += f"\n[Avatar Embodiment & Wardrobe State]:\n{context}\n"
    if system_context:
        sys_prompt += f"\n{system_context}"

    res = call_local_chat(prompt, sys_prompt, endpoint, model)
    if res["success"]:
        emit_state("speaking")
        dispatch_event("agent_response", {"content": res["content"]})
        return res["content"]
    else:
        dispatch_event("error", {"message": res["error"]})
        return res["error"]

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HINATA Agent Bridge")
    parser.add_argument("-q", "--query", type=str, help="Query for HINATA")
    parser.add_argument("-c", "--context", type=str, default="", help="Runtime context/wardrobe")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL, help="Model name")
    parser.add_argument("--test", action="store_true", help="Run self-test")
    args = parser.parse_args()

    if args.test:
        print(run_query("Report GPU and RAM status.", model=args.model))
    elif args.query:
        run_query(args.query, context=args.context, model=args.model)
    else:
        parser.print_help()
