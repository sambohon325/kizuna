from __future__ import annotations

import math
import subprocess
import struct
import wave
from pathlib import Path

from app.animatic import ffmpeg_executable


def generate_timing_slate(path: Path, text: str, duration_seconds: float, pitch_semitones: float = 0, pace: float = 1.0) -> None:
    """Create a speech-shaped timing slate without impersonating a real voice."""
    sample_rate = 48_000
    duration = max(0.25, float(duration_seconds))
    sample_count = int(sample_rate * duration)
    words = max(1, len(text.split()))
    pulses = max(1, min(words, int(duration * 4 * max(.5, pace))))
    base = 185 * (2 ** (pitch_semitones / 12))
    frames = bytearray()
    for index in range(sample_count):
        time = index / sample_rate
        phase = (time / duration) * pulses
        local = phase - math.floor(phase)
        envelope = max(0, 1 - abs(local - .32) / .32) ** 1.8
        attack = min(1, time / .02)
        release = min(1, (duration - time) / .04)
        modulation = 1 + .035 * math.sin(2 * math.pi * 5.2 * time)
        sample = math.sin(2 * math.pi * base * modulation * time)
        sample += .28 * math.sin(2 * math.pi * base * 2.01 * time)
        value = int(max(-1, min(1, sample * envelope * attack * release * .22)) * 32767)
        frames.extend(struct.pack("<h", value))
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        output.writeframes(frames)


def split_audio_file(source: Path, first: Path, second: Path, split_seconds: float, total_seconds: float) -> None:
    """Create two non-destructive WAV regions while preserving the source file."""
    if not source.is_file():
        raise FileNotFoundError(source)
    parts = ((first, 0.0, split_seconds), (second, split_seconds, total_seconds - split_seconds))
    created: list[Path] = []
    try:
        for output, offset, duration in parts:
            command = [ffmpeg_executable(), "-y", "-loglevel", "error", "-ss", f"{offset:.4f}", "-i", str(source), "-t", f"{duration:.4f}", "-vn", "-acodec", "pcm_s16le", str(output)]
            completed = subprocess.run(command, capture_output=True, text=True, timeout=120)
            if completed.returncode:
                raise RuntimeError(completed.stderr[-2000:] or "FFmpeg could not split the audio region")
            created.append(output)
    except Exception:
        for output in created:
            output.unlink(missing_ok=True)
        raise
