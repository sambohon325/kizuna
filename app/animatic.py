from __future__ import annotations

import subprocess
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

from app.config import settings


def ffmpeg_executable() -> str:
    if settings.ffmpeg_path:
        return settings.ffmpeg_path
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def _font(size: int):
    for path in ("C:/Windows/Fonts/segoeui.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def prepare_frame(source: Path | None, target: Path, width: int, height: int, title: str, subtitle: str) -> None:
    canvas = Image.new("RGB", (width, height), "#11131a")
    if source and source.exists():
        try:
            with Image.open(source) as opened:
                frame = ImageOps.contain(opened.convert("RGB"), (width, height))
                canvas.paste(frame, ((width - frame.width) // 2, (height - frame.height) // 2))
        except Exception:
            pass
    draw = ImageDraw.Draw(canvas)
    band_height = max(62, height // 7)
    draw.rectangle((0, height - band_height, width, height), fill=(8, 10, 15, 225))
    title_font = _font(max(16, min(42, width // 36)))
    meta_font = _font(max(11, min(24, width // 60)))
    draw.text((width * .04, height - band_height * .76), title, fill="#f6f0e7", font=title_font)
    draw.text((width * .04, height - band_height * .30), subtitle, fill="#e56a54", font=meta_font)
    if not source or not source.exists():
        draw.text((width * .04, height * .10), "KIZUNA  /  ANIMATIC FRAME", fill="#5d6475", font=meta_font)
        wrapped = textwrap.fill(title, width=max(18, width // 28))
        draw.multiline_text((width * .08, height * .34), wrapped, fill="#d9d4ca", font=title_font, spacing=8)
    canvas.save(target, "PNG")


def render_animatic(clips: list[dict], output: Path, work_dir: Path, fps: int, width: int, height: int, audio_clips: list[dict] | None = None, watermark_text: str = "", max_duration_seconds: float | None = None) -> None:
    if not clips:
        raise ValueError("The timeline has no clips")
    work_dir.mkdir(parents=True, exist_ok=True)
    frames: list[Path] = []
    for index, clip in enumerate(clips):
        target = work_dir / f"frame-{index:04d}.png"
        prepare_frame(clip.get("source"), target, width, height, clip["title"], clip["subtitle"])
        frames.append(target)

    command = [ffmpeg_executable(), "-y"]
    for frame, clip in zip(frames, clips):
        command += ["-loop", "1", "-t", f"{clip['duration']:.3f}", "-i", str(frame)]
    command += ["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000"]
    usable_audio = [cue for cue in (audio_clips or []) if cue.get("source") and Path(cue["source"]).exists()]
    for cue in usable_audio:
        command += ["-i", str(cue["source"])]

    filters = [f"[{i}:v]fps={fps},scale={width}:{height},format=yuv420p,settb=AVTB[v{i}]" for i in range(len(clips))]
    current = "v0"
    elapsed = clips[0]["duration"]
    for i in range(1, len(clips)):
        requested = clips[i].get("transition_duration", 0) if clips[i].get("transition") != "cut" else 0
        duration = max(1 / fps, min(float(requested or 0), clips[i - 1]["duration"] / 2, clips[i]["duration"] / 2))
        offset = max(0, elapsed - duration)
        output_label = f"mix{i}"
        filters.append(f"[{current}][v{i}]xfade=transition=fade:duration={duration:.4f}:offset={offset:.4f}[{output_label}]")
        current = output_label
        elapsed = offset + clips[i]["duration"]
    if watermark_text:
        escaped = watermark_text.replace("\\", "\\\\").replace("'", "\\'").replace(":", "\\:")
        filters.append(f"[{current}]drawtext=text='{escaped}':fontcolor=white@0.92:fontsize=h/28:box=1:boxcolor=black@0.58:boxborderw=12:x=w-tw-24:y=h-th-24[trialmark]")
        current = "trialmark"
    silence_index = len(clips)
    filters.append(f"[{silence_index}:a]atrim=0:{elapsed:.4f},asetpts=PTS-STARTPTS[bed]")
    audio_labels = ["bed"]
    for index, cue in enumerate(usable_audio):
        input_index = silence_index + 1 + index
        delay = max(0, int(float(cue.get("start", 0)) * 1000))
        duration = max(.05, float(cue.get("duration", elapsed)))
        volume = max(0, min(2, float(cue.get("volume", 1))))
        label = f"cue{index}"
        filters.append(f"[{input_index}:a]atrim=0:{duration:.4f},asetpts=PTS-STARTPTS,adelay={delay}:all=1,volume={volume:.3f}[{label}]")
        audio_labels.append(label)
    if len(audio_labels) > 1:
        filters.append("".join(f"[{label}]" for label in audio_labels) + f"amix=inputs={len(audio_labels)}:duration=longest:normalize=0[audio]")
        audio_map = "[audio]"
    else:
        audio_map = "[bed]"
    output_duration = min(elapsed, max_duration_seconds) if max_duration_seconds else elapsed
    command += [
        "-filter_complex", ";".join(filters), "-map", f"[{current}]", "-map", audio_map,
        "-t", f"{output_duration:.3f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(output),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, timeout=max(120, int(elapsed * 3)))
    if completed.returncode:
        raise RuntimeError(completed.stderr[-3000:] or "FFmpeg failed")
