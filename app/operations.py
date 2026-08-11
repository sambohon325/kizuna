from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.config import settings
from app.job_queue import redis_client
from app.models import DurableJob, ProjectBackup
from app.schema_migrations import database_revision


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _check(key: str, label: str, state: str, summary: str, details: dict | None = None) -> dict:
    return {"key": key, "label": label, "state": state, "summary": summary, "details": details or {}}


def _disk_check(label: str, root: Path) -> dict:
    try:
        root = root.resolve()
        root.mkdir(parents=True, exist_ok=True)
        usage = shutil.disk_usage(root)
        free_gb = usage.free / (1024 ** 3)
        free_percent = usage.free / usage.total * 100 if usage.total else 0
        with tempfile.NamedTemporaryFile(prefix=".kizuna-readiness-", dir=root, delete=True) as probe:
            probe.write(b"ready")
            probe.flush()
        low = free_gb < settings.storage_warning_free_gb or free_percent < settings.storage_warning_free_percent
        state = "warning" if low else "ready"
        summary = f"{free_gb:.1f} GB free ({free_percent:.0f}%)" if not low else f"Low capacity: {free_gb:.1f} GB free ({free_percent:.0f}%)"
        return _check(f"disk-{label.casefold()}", f"{label} storage", state, summary, {"free_bytes": usage.free, "total_bytes": usage.total, "writable": True})
    except Exception:
        return _check(f"disk-{label.casefold()}", f"{label} storage", "error", "Storage is unavailable or not writable.", {"writable": False})


def operational_readiness(db: Session, storage_root: Path, render_root: Path, *, s3_configured: bool) -> dict:
    checks: list[dict] = []
    try:
        db.execute(text("SELECT 1"))
        checks.append(_check("database", "Database", "ready", "Database queries are responding.", {"revision": database_revision()}))
    except Exception:
        checks.append(_check("database", "Database", "error", "The database did not answer a readiness query."))

    if settings.redis_url:
        client = redis_client()
        try:
            if client is None or not client.ping():
                raise RuntimeError("Redis unavailable")
            checks.append(_check("redis", "Job wake-ups", "ready", "Redis is connected; workers receive immediate queue notifications."))
        except Exception:
            checks.append(_check("redis", "Job wake-ups", "warning", "Redis is configured but unavailable. Database polling remains active."))
    else:
        checks.append(_check("redis", "Job wake-ups", "warning", "Redis is not configured. Local database polling is handling job wake-ups."))

    checks.append(_disk_check("Production", storage_root))
    if render_root.resolve() != storage_root.resolve():
        checks.append(_disk_check("Render", render_root))

    counts = dict(db.execute(select(DurableJob.status, func.count(DurableJob.id)).group_by(DurableJob.status)).all())
    now = utcnow()
    expired = db.scalar(select(func.count(DurableJob.id)).where(DurableJob.status == "running", DurableJob.leased_until.is_not(None), DurableJob.leased_until < now)) or 0
    oldest_queued = db.scalar(select(func.min(DurableJob.created_at)).where(DurableJob.status == "queued"))
    recent_failed = db.scalar(select(func.count(DurableJob.id)).where(DurableJob.status == "failed", DurableJob.updated_at >= now - timedelta(hours=24))) or 0
    queued_age = max(0, int((now - oldest_queued).total_seconds())) if oldest_queued else 0
    job_state = "error" if expired else "warning" if recent_failed or queued_age > 120 else "ready"
    if expired:
        job_summary = f"{expired} worker lease{'s' if expired != 1 else ''} expired and need recovery."
    elif recent_failed:
        job_summary = f"{recent_failed} job{'s' if recent_failed != 1 else ''} failed in the last 24 hours."
    elif queued_age > 120:
        job_summary = f"The oldest queued job has waited {queued_age // 60} minutes."
    else:
        job_summary = "The durable queue has no current recovery warnings."
    checks.append(_check("jobs", "Durable jobs", job_state, job_summary, {"queued": counts.get("queued", 0), "running": counts.get("running", 0), "completed": counts.get("completed", 0), "failed": counts.get("failed", 0), "cancelled": counts.get("cancelled", 0), "expired_leases": expired, "oldest_queued_seconds": queued_age}))

    latest = db.scalar(select(ProjectBackup).where(ProjectBackup.status == "completed").order_by(ProjectBackup.created_at.desc(), ProjectBackup.id.desc()))
    if latest is None:
        checks.append(_check("backups", "Production backups", "warning", "No completed production backup exists yet.", {"s3_configured": s3_configured}))
    else:
        backend, separator, key = latest.storage_key.partition(":")
        if not separator:
            backend, key = "local", latest.storage_key
        archive_path = (storage_root / key).resolve()
        root = storage_root.resolve()
        local_exists = backend != "local" or (root in archive_path.parents and archive_path.is_file())
        backup_state = "ready" if local_exists else "error"
        backup_summary = f"Latest backup completed {latest.created_at.isoformat()}Z." if local_exists else "The latest local backup record exists, but its archive is missing."
        checks.append(_check("backups", "Production backups", backup_state, backup_summary, {"id": latest.id, "project_id": latest.project_id, "backend": backend, "size_bytes": latest.size_bytes, "checksum_recorded": bool(latest.checksum_sha256), "deep_verification_available": backend == "local" and local_exists, "s3_configured": s3_configured}))

    states = {item["state"] for item in checks}
    status = "error" if "error" in states else "warning" if "warning" in states else "ready"
    return {"status": status, "checked_at": utcnow().isoformat() + "Z", "environment": settings.environment, "checks": checks}


def verify_local_backup(backup: ProjectBackup, storage_root: Path) -> dict:
    backend, separator, key = backup.storage_key.partition(":")
    if not separator:
        backend, key = "local", backup.storage_key
    if backend != "local":
        raise ValueError("Deep verification currently requires a local backup archive.")
    archive_path = (storage_root / key).resolve()
    root = storage_root.resolve()
    if root not in archive_path.parents or not archive_path.is_file():
        raise FileNotFoundError("The local backup archive is missing.")
    digest = hashlib.sha256()
    with archive_path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    if not backup.checksum_sha256 or digest.hexdigest() != backup.checksum_sha256:
        raise ValueError("The backup checksum does not match its stored audit record.")
    try:
        with ZipFile(archive_path) as archive:
            damaged = archive.testzip()
            if damaged:
                raise ValueError(f"The backup contains a damaged entry: {damaged}")
            manifest = json.loads(archive.read("manifest.json"))
            if manifest.get("format") != "kizuna-project-backup" or manifest.get("version") != 1:
                raise ValueError("The backup manifest format is not supported.")
            if int(manifest.get("project", {}).get("id", 0)) != backup.project_id:
                raise ValueError("The backup manifest belongs to another production.")
            entries = len(archive.infolist())
    except (BadZipFile, KeyError) as exc:
        raise ValueError("The backup is not a complete Kizuna archive.") from exc
    return {"verified": True, "backup_id": backup.id, "project_id": backup.project_id, "filename": backup.filename, "checksum_sha256": backup.checksum_sha256, "entries": entries, "verified_at": utcnow().isoformat() + "Z", "message": "Checksum, archive entries, manifest, and production identity all passed."}
