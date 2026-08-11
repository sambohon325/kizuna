from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Callable

from app.animatic import ffmpeg_executable, run_ffmpeg


def segment_clip_ranges(clips: list[dict], target_size: int) -> list[tuple[int, int]]:
    ranges = []
    start = 0
    while start < len(clips):
        end = min(len(clips), start + target_size)
        while end < len(clips) and clips[end].get("transition") != "cut":
            end += 1
        ranges.append((start, end))
        start = end
    return ranges


def clip_start_times(clips: list[dict], fps: int) -> list[float]:
    if not clips:
        return []
    starts = [0.0]
    elapsed = float(clips[0]["duration_seconds"])
    for index in range(1, len(clips)):
        requested = clips[index].get("transition_duration", 0) if clips[index].get("transition") != "cut" else 0
        duration = max(1 / fps, min(float(requested or 0), clips[index - 1]["duration_seconds"] / 2, clips[index]["duration_seconds"] / 2))
        start = max(0, elapsed - duration)
        starts.append(start)
        elapsed = start + clips[index]["duration_seconds"]
    return starts


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def assemble_segments(segment_files: list[Path], output: Path, work_dir: Path, watermark_text: str = "", max_duration_seconds: float | None = None, status_callback: Callable[[], bool | None] | None = None) -> None:
    if not segment_files:
        raise ValueError("No completed segments to assemble")
    work_dir.mkdir(parents=True, exist_ok=True)
    concat_file = work_dir / "segments.txt"
    lines = [f"file '{str(path.resolve()).replace(chr(39), chr(39) + chr(92) + chr(39) + chr(39))}'" for path in segment_files]
    concat_file.write_text("\n".join(lines), encoding="utf-8")
    command = [ffmpeg_executable(), "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(concat_file)]
    if watermark_text:
        escaped = watermark_text.replace("\\", "\\\\").replace("'", "\\'").replace(":", "\\:")
        command += ["-vf", f"drawtext=text='{escaped}':fontcolor=white@0.92:fontsize=h/28:box=1:boxcolor=black@0.58:boxborderw=12:x=w-tw-24:y=h-th-24", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-c:a", "aac", "-b:a", "192k"]
    else:
        command += ["-c", "copy"]
    if max_duration_seconds:
        command += ["-t", f"{max_duration_seconds:.3f}"]
    command += ["-movflags", "+faststart", str(output)]
    run_ffmpeg(command, 300, "Segment assembly failed", status_callback)
