from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.config import settings
from app.job_queue import redis_client
from app.models import DurableJob, ProjectBackup, ServiceHeartbeat
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


def _service_checks(db: Session, now: datetime) -> list[dict]:
    rows = db.scalars(select(ServiceHeartbeat).order_by(ServiceHeartbeat.last_seen.desc())).all()
    latest: dict[str, ServiceHeartbeat] = {}
    instances: dict[str, int] = {}
    stale_after = max(15, settings.service_stale_seconds)
    for row in rows:
        if max(0, int((now - row.last_seen).total_seconds())) <= stale_after:
            instances[row.service_key] = instances.get(row.service_key, 0) + 1
        latest.setdefault(row.service_key, row)
    required = ["web"]
    if not settings.job_inline_fallback:
        required.append("job-worker")
    if settings.environment.casefold() == "production":
        required.append("backup-scheduler")
    labels = {"web": "Web application", "job-worker": "Background job worker", "backup-scheduler": "Backup scheduler"}
    checks = []
    for service_key in dict.fromkeys(required + sorted(latest)):
        row = latest.get(service_key)
        if row is None:
            state = "error" if settings.environment.casefold() == "production" else "warning"
            checks.append(_check(f"service-{service_key}", labels.get(service_key, service_key), state, "No service heartbeat has been recorded.", {"instances": 0, "last_seen_seconds": None}))
            continue
        age = max(0, int((now - row.last_seen).total_seconds()))
        stale = age > stale_after
        state = "error" if stale or row.status == "error" else "warning" if row.status not in {"ready", "online"} else "ready"
        active_instances = instances.get(service_key, 0)
        summary = f"Heartbeat received {age} seconds ago from {active_instances} instance{'s' if active_instances != 1 else ''}."
        if stale:
            summary = f"Last heartbeat was {age} seconds ago. Restart or inspect this service in Coolify."
        checks.append(_check(f"service-{service_key}", labels.get(service_key, service_key), state, summary, {"instances": active_instances, "last_seen_seconds": age, "instance_id": row.instance_id, "service_status": row.status}))
    return checks


def _scanner_check() -> dict:
    if not settings.scanner_health_url:
        state = "error" if settings.environment.casefold() == "production" else "warning"
        return _check("service-compliance-scanner", "Compliance scanner", state, "No scanner health address is configured.", {"configured": False})
    try:
        with urllib.request.urlopen(settings.scanner_health_url, timeout=2) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if response.status != 200 or payload.get("status") != "ok":
            raise ValueError("Scanner health response was not ready")
        return _check("service-compliance-scanner", "Compliance scanner", "ready", "The originality reference scanner is responding.", {"configured": True, "records": payload.get("records", 0), "corpus_revision": payload.get("revision", "")})
    except (OSError, ValueError, json.JSONDecodeError, urllib.error.URLError):
        return _check("service-compliance-scanner", "Compliance scanner", "error", "The configured scanner did not answer its health check.", {"configured": True})


def _alerts(checks: list[dict]) -> list[dict]:
    local = settings.environment.casefold() != "production"
    actions = {
        "redis": "No action is required for simple local use; enable Redis before testing the distributed production stack." if local else "Inspect Redis in Coolify; database polling remains available while it recovers.",
        "jobs": "Open Activity, inspect the failed or expired jobs, then retry only after resolving the cause.",
        "backups": "Create and verify a production backup before relying on disaster recovery.",
        "restore-drill": "Run a recovery drill after creating a local backup, then investigate any failed archive entry before relying on it.",
        "service-web": "Inspect the web service logs and restart the container if its heartbeat remains stale.",
        "service-job-worker": "Inspect job-worker logs; queued renders will wait until the worker returns.",
        "service-backup-scheduler": "Inspect backup-scheduler logs and manually confirm the next scheduled backup.",
        "service-compliance-scanner": "Connect the self-hosted scanner before testing corpus-backed originality checks." if local else "Inspect the compliance-scanner container and its corpus health endpoint.",
    }
    alerts = []
    for check in checks:
        if check["state"] == "ready":
            continue
        action = actions.get(check["key"], "Review this check before starting a long render or export.")
        if check["key"].startswith("disk-"):
            action = "Free space or expand this volume before starting large renders and backups."
        alerts.append({"key": check["key"], "severity": check["state"], "title": check["label"], "message": check["summary"], "action": action})
    return alerts


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

    checks.extend(_service_checks(db, now))
    checks.append(_scanner_check())

    drill = db.scalar(select(DurableJob).where(DurableJob.kind == "maintenance.restore-drill").order_by(DurableJob.created_at.desc(), DurableJob.id.desc()))
    drill_result = (drill.result or {}) if drill else {}
    if drill is None:
        checks.append(_check("restore-drill", "Recovery drill", "warning", "No backup recovery drill has been recorded yet.", {"job_id": None, "status": "never"}))
    elif drill.status == "completed" and drill_result.get("passed"):
        overdue = drill.created_at < now - timedelta(hours=max(1, settings.restore_drill_interval_hours) * 2)
        drill_state = "warning" if overdue else "ready"
        drill_summary = "The last recovery rehearsal passed." if not overdue else "The last successful recovery rehearsal is overdue for renewal."
        checks.append(_check("restore-drill", "Recovery drill", drill_state, drill_summary, {"job_id": drill.id, "status": drill.status, "backup_id": drill_result.get("backup_id"), "expanded_bytes": drill_result.get("expanded_bytes", 0), "recovered_assets": drill_result.get("recovered_assets", 0), "duration_seconds": drill_result.get("duration_seconds", 0), "completed_at": drill.completed_at.isoformat() + "Z" if drill.completed_at else ""}))
    elif drill.status in {"queued", "running"}:
        checks.append(_check("restore-drill", "Recovery drill", "warning", f"A recovery drill is {drill.status}.", {"job_id": drill.id, "status": drill.status, "progress_percent": drill.progress_percent}))
    else:
        checks.append(_check("restore-drill", "Recovery drill", "error", "The latest recovery drill did not pass.", {"job_id": drill.id, "status": drill.status, "error": bool(drill.error)}))

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
        checks.append(_check("backups", "Production backups", backup_state, backup_summary, {"id": latest.id, "project_id": latest.project_id, "backend": backend, "size_bytes": latest.size_bytes, "checksum_recorded": bool(latest.checksum_sha256), "deep_verification_available": backend == "local" and local_exists, "restore_drill_available": backend == "local" and local_exists, "s3_configured": s3_configured}))

    states = {item["state"] for item in checks}
    status = "error" if "error" in states else "warning" if "warning" in states else "ready"
    return {"status": status, "checked_at": utcnow().isoformat() + "Z", "environment": settings.environment, "checks": checks, "alerts": _alerts(checks)}


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
