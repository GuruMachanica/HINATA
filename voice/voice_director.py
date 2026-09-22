"""
HINATA Voice Director
Maps emotion, intent, and conversational context into TTS prosody parameters.
Modular and strictly decoupled.
"""

from typing import Dict, Any

EMOTION_PROSODY_MAP: Dict[str, Dict[str, Any]] = {
    "calm": {"rate": 0.98, "pitch": 0.0, "energy": 0.55, "pause_before_ms": 0},
    "confident": {"rate": 1.02, "pitch": 0.5, "energy": 0.70, "pause_before_ms": 50},
    "curious": {"rate": 1.04, "pitch": 1.0, "energy": 0.65, "pause_before_ms": 100},
    "concerned": {"rate": 0.92, "pitch": -0.5, "energy": 0.60, "pause_before_ms": 150},
    "thinking": {"rate": 0.95, "pitch": 0.0, "energy": 0.45, "pause_before_ms": 200},
    "neutral": {"rate": 1.00, "pitch": 0.0, "energy": 0.60, "pause_before_ms": 0},
}

def direct_speech(text: str, emotion: str = "calm", voice_id: str = "af_heart") -> Dict[str, Any]:
    """Generates a structured TTS instruction with prosody parameters."""
    prosody = EMOTION_PROSODY_MAP.get(emotion.lower(), EMOTION_PROSODY_MAP["neutral"])
    return {
        "text": text,
        "voice_id": voice_id,
        "emotion": emotion,
        "rate": prosody["rate"],
        "pitch": prosody["pitch"],
        "energy": prosody["energy"],
        "pause_before_ms": prosody["pause_before_ms"]
    }
