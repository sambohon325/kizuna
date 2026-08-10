from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.compliance import append_audit_event
from app.config import settings
from app.job_queue import update_progress
from app.models import AssetResidency, DurableJob, MediaCleanupReview, MediaStoragePolicy


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _server_source(uri: str) -> Path | None:
    if not uri.startswith("/renders/"):
        return None
    root = Path(settings.render_directory).resolve()
    path = (root / uri.removeprefix("/renders/")).resolve()
    return path if root in path.parents else None


def execute_storage_audit_job(db: Session, job: DurableJob) -> dict[str, Any]:
    """Re-check server originals and invalidate stale cleanup approvals without deleting files."""
    project_id = int(job.payload["project_id"])
    now = _utcnow()
    policy = db.scalar(select(MediaStoragePolicy).where(MediaStoragePolicy.project_id == project_id))
    required_replicas = policy.minimum_replicas if policy else 1
    cutoff = now - timedelta(hours=settings.cleanup_verification_hours)
    sources = db.scalars(select(AssetResidency).where(
        AssetResidency.project_id == project_id,
        AssetResidency.representation == "original",
        AssetResidency.backend == "server",
    ).order_by(AssetResidency.id)).all()
    reviews = {item.asset_key: item for item in db.scalars(select(MediaCleanupReview).where(MediaCleanupReview.project_id == project_id)).all()}
    copies = db.scalars(select(AssetResidency).where(
        AssetResidency.project_id == project_id,
        AssetResidency.representation == "original",
        AssetResidency.backend.in_(["hive", "s3"]),
    )).all()

    checked = changed = missing = approvals_reset = eligible = 0
    total = max(1, len(sources))
    for index, source in enumerate(sources, start=1):
        path = _server_source(source.uri)
        if path is None or not path.is_file():
            source.status = "missing"
            missing += 1
        else:
            checksum = _checksum(path)
            size = path.stat().st_size
            if checksum != source.checksum_sha256 or size != source.size_bytes:
                changed += 1
                append_audit_event(db, project_id, "asset", "original_changed", subject_type="original", subject_key=source.asset_key, details={"previous_checksum_sha256": source.checksum_sha256, "checksum_sha256": checksum, "size_bytes": size})
            source.checksum_sha256 = checksum
            source.size_bytes = size
            source.status = "available"
            source.last_verified_at = now
            checked += 1

        fresh = {
            (copy.backend, copy.node_key or copy.object_ref)
            for copy in copies
            if source.status == "available"
            and copy.asset_key == source.asset_key
            and copy.status == "available"
            and copy.checksum_sha256 == source.checksum_sha256
            and copy.last_verified_at
            and copy.last_verified_at >= cutoff
        }
        if len(fresh) >= required_replicas:
            eligible += 1
        review = reviews.get(source.asset_key)
        if review and review.status == "approved" and (source.status != "available" or review.checksum_sha256 != source.checksum_sha256 or len(fresh) < review.required_replicas):
            review.status = "review"
            review.approved_at = None
            review.note = "Approval reset automatically because the source or verified replica state changed."
            approvals_reset += 1
        update_progress(db, job, 10 + int(index / total * 80), f"Verified {index} of {len(sources)} server originals")

    append_audit_event(db, project_id, "storage", "maintenance_audit", subject_type="project", subject_key=str(project_id), details={"checked": checked, "changed": changed, "missing": missing, "eligible": eligible, "approvals_reset": approvals_reset, "deletion_performed": False})
    return {"checked": checked, "changed": changed, "missing": missing, "eligible": eligible, "approvals_reset": approvals_reset, "deletion_performed": False}
