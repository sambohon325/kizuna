from __future__ import annotations

import subprocess
from copy import deepcopy
from pathlib import Path
from typing import Callable

from PIL import Image

from app.animatic import ffmpeg_executable
from app.compositor import compose_frame


def _ease(progress: float, mode: str) -> float:
    progress = max(0, min(1, progress))
    if mode == "ease-in":
        return progress * progress
    if mode == "ease-out":
        return 1 - (1 - progress) ** 2
    if mode == "ease-in-out":
        return progress * progress * (3 - 2 * progress)
    return progress


def _lerp(start: float, end: float, progress: float) -> float:
    return start + (end - start) * progress


def _animated_layers(layers: list[dict], progress: float) -> list[dict]:
    output = []
    for original in layers:
        layer = deepcopy(original)
        animation = layer.get("animation") or {}
        end = animation.get("end") or {}
        eased = _ease(progress, animation.get("easing", "ease-in-out"))
        transform = dict(layer.get("transform") or {})
        for field, default in (("x", .5), ("y", .5), ("scale", 1), ("rotation", 0)):
            start_value = float(transform.get(field, default))
            transform[field] = _lerp(start_value, float(end.get(field, start_value)), eased)
        start_opacity = float(layer.get("opacity", 1))
        layer["opacity"] = _lerp(start_opacity, float(end.get("opacity", start_opacity)), eased)
        layer["transform"] = transform
        output.append(layer)
    return output


def _camera_frame(frame: Image.Image, camera: dict, progress: float) -> Image.Image:
    eased = _ease(progress, camera.get("easing", "ease-in-out"))
    start_scale = max(1, float(camera.get("start_scale", 1)))
    end_scale = max(1, float(camera.get("end_scale", start_scale)))
    scale = _lerp(start_scale, end_scale, eased)
    pan_x = float(camera.get("pan_x", 0)) * eased
    pan_y = float(camera.get("pan_y", 0)) * eased
    if scale == 1 and pan_x == 0 and pan_y == 0:
        return frame
    width, height = frame.size
    crop_width, crop_height = width / scale, height / scale
    center_x = width * (.5 + pan_x)
    center_y = height * (.5 + pan_y)
    left = max(0, min(width - crop_width, center_x - crop_width / 2))
    top = max(0, min(height - crop_height, center_y - crop_height / 2))
    crop = frame.crop((round(left), round(top), round(left + crop_width), round(top + crop_height)))
    return crop.resize((width, height), Image.Resampling.LANCZOS)


def render_motion_video(layers: list[dict], output: Path, width: int, height: int, fps: int, duration_seconds: float, color_grade: dict, camera: dict, progress_callback: Callable[[int, int], bool | None] | None = None) -> int:
    frame_count = max(1, round(duration_seconds * fps))
    command = [
        ffmpeg_executable(), "-y", "-loglevel", "error", "-f", "rawvideo", "-vcodec", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{width}x{height}", "-r", str(fps), "-i", "-", "-an", "-c:v", "libx264",
        "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output),
    ]
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    try:
        for index in range(frame_count):
            if progress_callback and (index == 0 or index % max(1, frame_count // 20) == 0):
                if progress_callback(index, frame_count) is False:
                    raise RuntimeError("Motion render cancelled")
            progress = index / max(1, frame_count - 1)
            frame = compose_frame(_animated_layers(layers, progress), width, height, color_grade)
            frame = _camera_frame(frame, camera, progress)
            process.stdin.write(frame.tobytes())
        process.stdin.close()
        if progress_callback and progress_callback(frame_count, frame_count) is False:
            raise RuntimeError("Motion render cancelled")
        error = process.stderr.read()
        return_code = process.wait(timeout=max(120, int(duration_seconds * 5)))
    except Exception:
        process.kill()
        raise
    if return_code:
        raise RuntimeError(error.decode("utf-8", errors="replace")[-3000:] or "FFmpeg motion render failed")
    return frame_count
