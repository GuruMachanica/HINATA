"""
HINATA Brain — real Hermes Agent (NousResearch) adapter for the Gateway.

Runs the actual vendored Hermes AIAgent (vendor/hermes-agent) with full
tool-calling, pointed at the local Ollama dolphin3 model. Falls back to a
direct OpenAI-compatible chat call when the Hermes runtime cannot initialize
(missing deps, no config home, etc.), so the product never hard-fails.

Emits Bella-style mood tags with every reply so the shell can drive VRM
expressions and animation.
"""

import json
import logging
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

log = logging.getLogger("hinata.brain")

ROOT_DIR = Path(__file__).resolve().parent.parent
HERMES_DIR = ROOT_DIR / "vendor" / "hermes-agent"
SOUL_PATH = ROOT_DIR / "hermes-core" / "config" / "SOUL.md"

DEFAULT_ENDPOINT = os.getenv("HERMES_MODEL_ENDPOINT", "http://127.0.0.1:11434/v1")
# hinata-brain = heretic-org/Qwen-3-VL-2B-Instruct-heretic (Q4_K_M GGUF in Ollama,
# with the HINATA persona baked into its system prompt).
DEFAULT_MODEL = os.getenv("HERMES_MODEL_NAME", "hinata-brain")

# Bella mood vocabulary -> (VRM expression hint, animation intent)
MOODS = {
    "happy":     {"expression": "happy",     "anim": "vrma-02"},
    "excited":   {"expression": "happy",     "anim": "vrma-07"},
    "curious":   {"expression": "relaxed",   "anim": "vrma-04"},
    "calm":      {"expression": "relaxed",   "anim": None},
    "neutral":   {"expression": "neutral",   "anim": None},
    "concerned": {"expression": "sad",       "anim": "vrma-05"},
    "sad":       {"expression": "sad",       "anim": "vrma-05"},
    "angry":     {"expression": "angry",     "anim": "vrma-05"},
}

MOOD_RE = re.compile(r"\[mood:\s*([a-z_]+)\]", re.IGNORECASE)

_system_prompt_cache = None


def load_system_prompt() -> str:
    """HINATA persona from SOUL.md, refreshed if the file changes."""
    global _system_prompt_cache
    try:
        text = SOUL_PATH.read_text(encoding="utf-8")
        _system_prompt_cache = text
        return text
    except OSError:
        return _system_prompt_cache or (
            "You are HINATA (Human-like Intelligent Nurturing Autonomous Tomodachi Architecture), "
            "an intelligent desktop AI companion embodied as a 3D VRM avatar. "
            "Be concise, warm and technically sharp."
        )


def detect_mood(reply: str) -> str:
    m = MOOD_RE.search(reply)
    if m:
        mood = m.group(1).lower()
        if mood in MOODS:
            return mood
    lower = reply.lower()
    if any(w in lower for w in ("great news", "awesome", "perfect!", "congrat")):
        return "happy"
    if any(w in lower for w in ("warning", "critical", "failed", "error", "problem")):
        return "concerned"
    if any(w in lower for w in ("interesting", "let's look", "let me check", "curious")):
        return "curious"
    return "neutral"


def clean_reply(reply: str) -> str:
    """Strip the [mood: x] tag and trailing whitespace from a reply."""
    return MOOD_RE.sub("", reply).strip()


def ensure_persona_installed():
    """Install the HINATA persona into the Hermes home (SOUL.md identity slot).

    Hermes resolves its identity from <HERMES_HOME>/SOUL.md, so that's where
    our persona belongs. Re-copies when our hermes-core/config/SOUL.md changes.
    """
    try:
        import hermes_bootstrap  # noqa: F401
        from hermes_constants import get_hermes_home
        hermes_home = Path(get_hermes_home())
        target = hermes_home / "SOUL.md"
        src = SOUL_PATH
        if src.exists() and (not target.exists() or target.read_text(encoding="utf-8") != src.read_text(encoding="utf-8")):
            hermes_home.mkdir(parents=True, exist_ok=True)
            target.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
            log.info("HINATA persona installed to %s", target)
    except Exception as e:
        log.debug("persona install skipped: %s", e)


def _run_real_hermes(prompt: str):
    """Run the vendored NousResearch Hermes AIAgent. Returns (reply, engine) or None."""
    if not (HERMES_DIR / "run_agent.py").exists():
        log.warning("hermes-agent checkout missing at %s", HERMES_DIR)
        return None
    if str(HERMES_DIR) not in sys.path:
        sys.path.insert(0, str(HERMES_DIR))
    try:
        from run_agent import AIAgent  # noqa: E402  (vendored)
    except Exception as e:
        log.warning("Hermes AIAgent import failed (%s); using fallback brain", e)
        return None

    ensure_persona_installed()
    try:
        # hinata-brain (heretic Qwen3-VL 2B) has no native Ollama tool-calling,
        # so run the real Hermes agent with all toolsets disabled — it acts as
        # the conversation/persona layer while we keep zero cloud dependencies.
        agent = AIAgent(
            base_url=DEFAULT_ENDPOINT,
            model=DEFAULT_MODEL,
            api_key="ollama",              # Ollama ignores the key; Hermes requires one
            max_iterations=2,
            enabled_toolsets=[],
            disabled_toolsets=None,
            quiet_mode=True,
        )
        result = agent.run_conversation(prompt)
        reply = (result or {}).get("final_response") or ""
        if reply.strip():
            return reply, "hermes"
    except Exception as e:
        log.warning("Hermes agent run failed (%s); using fallback brain", e)
    return None


def _run_fallback(prompt: str):
    """Direct OpenAI-compatible chat to local Ollama. Returns (reply, engine) or None."""
    payload = {
        "model": DEFAULT_MODEL,
        "messages": [
            {"role": "system", "content": load_system_prompt()},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "temperature": 0.7,
    }
    req = urllib.request.Request(
        f"{DEFAULT_ENDPOINT}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            content = data["choices"][0]["message"]["content"]
            return content, "fallback"
    except Exception as e:
        log.error("Fallback brain failed: %s", e)
        return None


def think(prompt: str, context: dict = None) -> dict:
    """Full brain turn: reply text + Bella mood + VRM animation intent."""
    context = context or {}

    # Wardrobe/persona context injection (Bella-style emotional awareness)
    outfit = context.get("outfit")
    if outfit:
        prompt = f"[Avatar context: user sees HINATA wearing '{outfit}'.]\n{prompt}"

    started = time.time()
    result = _run_real_hermes(prompt)
    if result is None:
        result = _run_fallback(prompt)
    if result is None:
        reply = "I could not reach my local model. Is Ollama running?"
        engine = "none"
    else:
        reply, engine = result

    mood = detect_mood(reply)
    clean = clean_reply(reply)
    meta = MOODS.get(mood, MOODS["neutral"])

    return {
        "content": clean,
        "mood": mood,
        "expression": meta["expression"],
        "animation": meta["anim"],
        "engine": engine,
        "latency_ms": int((time.time() - started) * 1000),
        "model": DEFAULT_MODEL,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    q = sys.argv[1] if len(sys.argv) > 1 else "Report your GPU and RAM status."
    print(json.dumps(think(q), indent=2))
