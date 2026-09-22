"""
HINATA Shared Protocol Specifications
Defines event contracts between Agent Cortex, Memory, Voice Director, and Avatar.
"""

from dataclasses import dataclass, asdict, field
from typing import Optional, List, Dict, Any
from enum import Enum
import time

class EmotionType(str, Enum):
    CALM = "calm"
    CONFIDENT = "confident"
    CURIOUS = "curious"
    CONCERNED = "concerned"
    THINKING = "thinking"
    NEUTRAL = "neutral"

class GazeTarget(str, Enum):
    USER = "user"
    CAMERA = "camera"
    AWAY = "away"
    DOWN = "down"

@dataclass
class AvatarEvent:
    """Deterministic payload sent to Farah 3D engine."""
    emotion: str = EmotionType.CALM.value
    intensity: float = 0.5
    expression: str = "neutral"
    gaze: str = GazeTarget.CAMERA.value
    gesture: Optional[str] = None
    speaking: bool = False
    duration_ms: int = 1500
    phonemes: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

@dataclass
class VoiceDirectorDirective:
    """Directs TTS engine with prosody and timing."""
    text: str
    emotion: str = EmotionType.CALM.value
    rate: float = 1.0          # 0.90 to 1.15
    pitch: float = 0.0         # semitones adjustment
    energy: float = 0.6        # vocal intensity
    pause_before_ms: int = 0
    voice_id: str = "af_heart" # Kokoro female executive voice

    def to_dict(self) -> dict:
        return asdict(self)

@dataclass
class ProactiveDecision:
    """Outcome of the consciousness/opportunity engine."""
    should_interrupt: bool
    urgency: float             # 0.0 (info) to 1.0 (critical)
    importance: float          # 0.0 to 1.0
    reason: str
    message: Optional[str] = None
    action: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

@dataclass
class MemoryEntry:
    """Structure for multi-tier companion memory."""
    tier: str                  # "episodic", "semantic", "relationship", "procedural"
    key: str
    content: str
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)
