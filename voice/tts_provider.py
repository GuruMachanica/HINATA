"""
HINATA TTS Provider
Coordinates sentence splitting, Voice Director prosody, and audio payload formatting.
Strictly under 70 LOC.
"""

import sys
from pathlib import Path
from typing import List, Dict, Any

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "voice"))

from sentence_chunker import split_into_sentences
from voice_director import direct_speech

class TTSProvider:
    def __init__(self, default_voice: str = "af_heart"):
        self.default_voice = default_voice

    def process_text_stream(self, full_text: str, emotion: str = "calm") -> List[Dict[str, Any]]:
        """Splits full response into individual speech directives for streaming playback."""
        sentences = split_into_sentences(full_text)
        speech_frames = []

        for idx, sentence in enumerate(sentences):
            if not sentence:
                continue
            directive = direct_speech(sentence, emotion=emotion, voice_id=self.default_voice)
            speech_frames.append({
                "sequence": idx + 1,
                "total_sentences": len(sentences),
                "directive": directive
            })

        return speech_frames
