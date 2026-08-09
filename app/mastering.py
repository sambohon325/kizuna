from __future__ import annotations

import subprocess
from pathlib import Path

from app.animatic import ffmpeg_executable, prepare_frame


def render_timeline_master(clips: list[dict], audio_clips: list[dict], output: Path, work_dir: Path, fps: int, width: int, height: int, watermark_text: str = "", max_duration_seconds: float | None = None) -> dict:
    if not clips:
        raise ValueError("The timeline has no clips")
    work_dir.mkdir(parents=True, exist_ok=True)
    command = [ffmpeg_executable(), "-y", "-loglevel", "error"]
    motion_count = 0
    for index, clip in enumerate(clips):
        motion = clip.get("motion_source")
        if motion and Path(motion).exists():
            command += ["-stream_loop", "-1", "-t", f"{clip['duration']:.3f}", "-i", str(motion)]
            motion_count += 1
        else:
            frame = work_dir / f"master-frame-{index:04d}.png"
            prepare_frame(clip.get("still_source"), frame, width, height, clip["title"], clip["subtitle"])
            command += ["-loop", "1", "-t", f"{clip['duration']:.3f}", "-i", str(frame)]

    silence_index = len(clips)
    command += ["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000"]
    usable_audio = [cue for cue in audio_clips if cue.get("source") and Path(cue["source"]).exists()]
    for cue in usable_audio:
        command += ["-i", str(cue["source"])]

    filters = []
    for index, clip in enumerate(clips):
        filters.append(
            f"[{index}:v]trim=duration={clip['duration']:.4f},setpts=PTS-STARTPTS,fps={fps},"
            f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,format=yuv420p,settb=AVTB[v{index}]"
        )
    current = "v0"
    elapsed = float(clips[0]["duration"])
    transitions = {"cut": "fade", "dissolve": "fade", "fade": "fadeblack"}
    for index in range(1, len(clips)):
        requested = clips[index].get("transition_duration", 0) if clips[index].get("transition") != "cut" else 0
        duration = max(1 / fps, min(float(requested or 0), clips[index - 1]["duration"] / 2, clips[index]["duration"] / 2))
        offset = max(0, elapsed - duration)
        output_label = f"mastermix{index}"
        transition = transitions.get(clips[index].get("transition", "cut"), "fade")
        filters.append(f"[{current}][v{index}]xfade=transition={transition}:duration={duration:.4f}:offset={offset:.4f}[{output_label}]")
        current = output_label
        elapsed = offset + clips[index]["duration"]

    if watermark_text:
        escaped = watermark_text.replace("\\", "\\\\").replace("'", "\\'").replace(":", "\\:")
        filters.append(f"[{current}]drawtext=text='{escaped}':fontcolor=white@0.92:fontsize=h/28:box=1:boxcolor=black@0.58:boxborderw=12:x=w-tw-24:y=h-th-24[trialmark]")
        current = "trialmark"

    filters.append(f"[{silence_index}:a]atrim=0:{elapsed:.4f},asetpts=PTS-STARTPTS[bed]")
    audio_labels = ["bed"]
    for index, cue in enumerate(usable_audio):
        input_index = silence_index + 1 + index
        delay = max(0, int(float(cue.get("start", 0)) * 1000))
        duration = max(.05, float(cue.get("duration", elapsed)))
        volume = max(0, min(2, float(cue.get("volume", 1))))
        label = f"mastercue{index}"
        filters.append(f"[{input_index}:a]atrim=0:{duration:.4f},asetpts=PTS-STARTPTS,adelay={delay}:all=1,volume={volume:.3f}[{label}]")
        audio_labels.append(label)
    if len(audio_labels) > 1:
        filters.append("".join(f"[{label}]" for label in audio_labels) + f"amix=inputs={len(audio_labels)}:duration=longest:normalize=0[masteraudio]")
        audio_map = "[masteraudio]"
    else:
        audio_map = "[bed]"

    output_duration = min(elapsed, max_duration_seconds) if max_duration_seconds else elapsed
    command += [
        "-filter_complex", ";".join(filters), "-map", f"[{current}]", "-map", audio_map,
        "-t", f"{output_duration:.3f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(output),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, timeout=max(300, int(elapsed * 8)))
    if completed.returncode:
        raise RuntimeError(completed.stderr[-4000:] or "FFmpeg master render failed")
    return {"motion_clips": motion_count, "fallback_clips": len(clips) - motion_count, "audio_cues": len(usable_audio), "duration_seconds": round(output_duration, 3), "watermarked": bool(watermark_text)}
