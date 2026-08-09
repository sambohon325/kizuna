from __future__ import annotations

import hashlib
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.animatic import ffmpeg_executable
from app.config import settings
from app.compliance import append_audit_event
from app.models import AssetResidency, DurableJob
from app.segmented_export import sha256_file


IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
VIDEO_SUFFIXES = {".mp4", ".mov", ".mkv", ".webm"}
AUDIO_SUFFIXES = {".wav", ".mp3", ".m4a", ".ogg", ".flac"}


def proxy_spec(project_id: int, asset_key: str, source: Path) -> tuple[str, str, Path] | None:
    suffix = source.suffix.lower()
    kind = "image" if suffix in IMAGE_SUFFIXES else "video" if suffix in VIDEO_SUFFIXES else "audio" if suffix in AUDIO_SUFFIXES else ""
    if not kind:
        return None
    extension = ".jpg" if kind == "image" else ".mp4" if kind == "video" else ".m4a"
    filename = f"{hashlib.sha256(asset_key.encode()).hexdigest()[:24]}{extension}"
    root = (Path(settings.storage_directory) / "proxies" / f"project-{project_id}").resolve()
    destination = (root / filename).resolve()
    if root not in destination.parents:
        return None
    return kind, filename, destination


def generate_proxy(source: Path, destination: Path, kind: str, width: int) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        if kind == "image":
            with Image.open(source) as image:
                image.thumbnail((width, width))
                image.convert("RGB").save(destination, "JPEG", quality=88, optimize=True)
        elif kind == "video":
            command = [ffmpeg_executable(), "-y", "-loglevel", "error", "-i", str(source), "-map", "0:v:0", "-map", "0:a?", "-vf", f"scale={width}:-2:force_original_aspect_ratio=decrease", "-c:v", "libx264", "-preset", "veryfast", "-crf", "28", "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", str(destination)]
            completed = subprocess.run(command, capture_output=True, text=True, timeout=300)
            if completed.returncode:
                raise OSError(completed.stderr[-2000:] or "Video proxy failed")
        else:
            command = [ffmpeg_executable(), "-y", "-loglevel", "error", "-i", str(source), "-vn", "-c:a", "aac", "-b:a", "128k", str(destination)]
            completed = subprocess.run(command, capture_output=True, text=True, timeout=180)
            if completed.returncode:
                raise OSError(completed.stderr[-2000:] or "Audio proxy failed")
    except (OSError, subprocess.TimeoutExpired, UnidentifiedImageError):
        destination.unlink(missing_ok=True)
        raise


def _source_path(source_uri: str) -> Path:
    prefix = "/renders/"
    if not source_uri.startswith(prefix):
        raise ValueError("Proxy source must be a Kizuna render asset")
    root = Path(settings.render_directory).resolve()
    source = (root / source_uri.removeprefix(prefix)).resolve()
    if root not in source.parents or not source.is_file():
        raise FileNotFoundError("Proxy source is missing or outside the render vault")
    return source


def execute_media_proxy_job(db: Session, job: DurableJob) -> dict[str, Any]:
    project_id = int(job.payload["project_id"])
    asset_key = str(job.payload["asset_key"])
    source = _source_path(str(job.payload["source_uri"]))
    spec = proxy_spec(project_id, asset_key, source)
    if spec is None:
        raise ValueError(f"Unsupported proxy source: {source.suffix}")
    kind, filename, destination = spec
    if not destination.is_file():
        generate_proxy(source, destination, kind, int(job.payload.get("proxy_width", 1280)))

    residency_key = hashlib.sha256(f"{project_id}|{asset_key}|proxy|server|".encode()).hexdigest()
    residency = db.scalar(select(AssetResidency).where(AssetResidency.residency_key == residency_key))
    changed = residency is None or not residency.checksum_sha256 or residency.uri != f"/api/media/proxies/{project_id}/{filename}"
    if residency is None:
        residency = AssetResidency(
            residency_key=residency_key,
            project_id=project_id,
            asset_key=asset_key,
            representation="proxy",
            backend="server",
        )
        db.add(residency)
    proxy_root = (Path(settings.storage_directory) / "proxies").resolve()
    residency.object_ref = str(destination.relative_to(proxy_root)).replace("\\", "/")
    residency.uri = f"/api/media/proxies/{project_id}/{filename}"
    residency.checksum_sha256 = sha256_file(destination)
    residency.size_bytes = destination.stat().st_size
    residency.status = "available"
    residency.last_verified_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.flush()
    if changed:
        append_audit_event(db, project_id, "asset", "output_registered", subject_type="proxy", subject_key=asset_key, details={"backend": "server", "uri": residency.uri, "checksum_sha256": residency.checksum_sha256, "size_bytes": residency.size_bytes})
    return {
        "residency_id": residency.id,
        "uri": residency.uri,
        "checksum_sha256": residency.checksum_sha256,
        "size_bytes": residency.size_bytes,
        "kind": kind,
    }
