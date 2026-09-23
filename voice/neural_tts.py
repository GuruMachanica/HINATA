"""
HINATA Neural TTS Engine (Edge-TTS / Natural Human Voice)
Generates studio-quality female speech; outputs base64 audio for
zero-dependency browser playback. Strictly under 75 LOC.
"""

import sys
import json
import base64
import asyncio
import argparse
import edge_tts

# en-US-AvaNeural: warmer, more expressive multilingual voice than Aria,
# with natural laughter/energy — the closest to a living companion.
DEFAULT_VOICE = "en-US-AvaNeural"
DEFAULT_RATE = "+8%"    # slightly brisk = confident, less robotic
DEFAULT_PITCH = "+2Hz"  # a touch brighter

async def generate_audio_bytes(text: str, voice: str = DEFAULT_VOICE,
                               rate: str = DEFAULT_RATE, pitch: str = DEFAULT_PITCH) -> bytes:
    """Synthesizes text to MP3 audio bytes using neural voice models."""
    communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    audio_data = bytearray()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data.extend(chunk["data"])
    return bytes(audio_data)

def synthesize_to_data_uri(text: str, voice: str = DEFAULT_VOICE,
                           rate: str = DEFAULT_RATE, pitch: str = DEFAULT_PITCH) -> str:
    """Returns base64 data URI string: data:audio/mp3;base64,..."""
    raw_bytes = asyncio.run(generate_audio_bytes(text, voice, rate, pitch))
    b64 = base64.b64encode(raw_bytes).decode("ascii")
    return f"data:audio/mp3;base64,{b64}"

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HINATA Neural TTS")
    parser.add_argument("text", type=str, help="Text to synthesize")
    parser.add_argument("--voice", type=str, default=DEFAULT_VOICE, help="Voice name")
    parser.add_argument("--rate", type=str, default=DEFAULT_RATE, help="Rate modifier (e.g. +5%)")
    parser.add_argument("--pitch", type=str, default=DEFAULT_PITCH, help="Pitch modifier (e.g. +2Hz)")
    args = parser.parse_args()

    try:
        uri = synthesize_to_data_uri(args.text, voice=args.voice, rate=args.rate, pitch=args.pitch)
        print(json.dumps({"success": True, "audio": uri, "text": args.text}))
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}))
