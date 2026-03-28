"""
audio.py — The Voice Booth
----------------------------
Converts a text script to an .mp3 file using edge-tts.

edge-tts uses Microsoft's neural text-to-speech engine — the same voices
built into Windows and the Edge browser. It's completely free, requires no
API key, and produces natural-sounding output suitable for extended listening.

Available voices: https://github.com/rany2/edge-tts#available-voices
Default: en-US-AriaNeural (clear, natural female voice)
Alternative: en-US-GuyNeural (male voice)
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import edge_tts


def _voice() -> str:
    # Read at call time (not import time) so .env is already loaded
    return os.getenv("TTS_VOICE", "en-US-AriaNeural")

def _output_dir() -> Path:
    return Path(os.getenv("AUDIO_OUTPUT_DIR", "./output"))


async def text_to_speech(
    script: str,
    filename: Optional[str] = None,
) -> Path:
    """
    Convert a text script to an .mp3 file using edge-tts (free, no API key).

    Args:
        script:   The spoken text to convert.
        filename: Output filename. Auto-generated with timestamp if not provided.

    Returns:
        Path to the saved .mp3 file.
    """
    output_dir = _output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)

    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"commute_radio_{timestamp}.mp3"

    output_path = output_dir / filename

    # edge-tts Communicate streams the audio in chunks and saves to disk.
    # Think of it like a phone call where the other side reads your script aloud
    # and we record the call directly to an mp3 file.
    communicate = edge_tts.Communicate(script, _voice())
    await communicate.save(str(output_path))

    return output_path
