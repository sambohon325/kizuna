from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Any
from uuid import uuid4

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.models import DurableJob, DurableJobEvent

try:
    import redis
except ImportError:  # Local development remains usable before optional services are installed.
    redis = None


TERMINAL_STATUSES = {"completed", "failed", "cancelled"}


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@lru_cache(maxsize=1)
def redis_client():
    if not settings.redis_url or redis is None:
        return None
    try:
        pool = redis.ConnectionPool.from_url(settings.redis_url, decode_responses=True)
        client = redis.Redis(connection_pool=pool)
        client.ping()
        return client
    except Exception:
        return None


def record_event(db: Session, job: DurableJob, message: str = "", data: dict[str, Any] | None = None) -> None:
    db.add(DurableJobEvent(
        job_id=job.id,
        status=job.status,
        progress_percent=job.progress_percent,
        message=message,
        event_data=data or {},
    ))


def notify_job(job: DurableJob) -> None:
    client = redis_client()
    if client is None:
        return
    try:
        client.xadd(
            settings.job_stream_key,
            {"job_id": str(job.id), "queue": job.queue, "kind": job.kind},
            maxlen=10_000,
            approximate=True,
        )
    except Exception:
        # The database ledger is authoritative; polling recovers a missed notification.
        redis_client.cache_clear()


def wait_for_notification(last_stream_id: str = "$", timeout_ms: int = 2000) -> str:
    """Wait for a Redis wake-up; database polling remains the recovery path."""
    client = redis_client()
    if client is None:
        return last_stream_id
    try:
        messages = client.xread({settings.job_stream_key: last_stream_id}, count=1, block=max(1, timeout_ms))
        if messages and messages[0][1]:
            return messages[0][1][-1][0]
    except Exception:
        redis_client.cache_clear()
    return last_stream_id


def enqueue_job(
    db: Session,
    kind: str,
    payload: dict[str, Any],
    *,
    project_id: int | None = None,
    queue: str = "default",
    priority: int = 50,
    max_attempts: int = 5,
    idempotency_key: str = "",
) -> DurableJob:
    seed = idempotency_key or uuid4().hex
    job_key = hashlib.sha256(f"{kind}|{seed}".encode()).hexdigest()
    existing = db.scalar(select(DurableJob).where(DurableJob.job_key == job_key))
    if existing is not None:
        return existing
    job = DurableJob(
        job_key=job_key,
        project_id=project_id,
        kind=kind,
        queue=queue,
        priority=max(0, min(100, priority)),
        payload=payload,
        max_attempts=max(1, max_attempts),
    )
    try:
        with db.begin_nested():
            db.add(job)
            db.flush()
    except IntegrityError:
        existing = db.scalar(select(DurableJob).where(DurableJob.job_key == job_key))
        if existing is None:
            raise
        return existing
    record_event(db, job, "Job queued")
    db.flush()
    notify_job(job)
    return job


def recover_expired_jobs(db: Session) -> int:
    now = utcnow()
    expired = db.scalars(select(DurableJob).where(
        DurableJob.status == "running",
        DurableJob.leased_until.is_not(None),
        DurableJob.leased_until < now,
    )).all()
    for job in expired:
        job.lease_owner = ""
        job.leased_until = None
        if job.cancellation_requested:
            job.status = "cancelled"
            job.completed_at = now
            record_event(db, job, "Cancellation applied after worker lease expired")
        elif job.attempts >= job.max_attempts:
            job.status = "failed"
            job.completed_at = now
            job.error = job.error or "Worker lease expired and retry limit was reached"
            record_event(db, job, job.error)
        else:
            job.status = "queued"
            job.next_attempt_at = now
            record_event(db, job, "Worker lease expired; job returned to queue")
            notify_job(job)
    return len(expired)


def claim_job(db: Session, worker_id: str, kinds: set[str] | None = None) -> DurableJob | None:
    recover_expired_jobs(db)
    now = utcnow()
    query = select(DurableJob).where(
        DurableJob.status == "queued",
        DurableJob.cancellation_requested.is_(False),
        or_(DurableJob.next_attempt_at.is_(None), DurableJob.next_attempt_at <= now),
    )
    if kinds:
        query = query.where(DurableJob.kind.in_(kinds))
    job = db.scalar(query.order_by(DurableJob.priority.desc(), DurableJob.id).with_for_update(skip_locked=True).limit(1))
    if job is None:
        return None
    start_job(db, job, worker_id)
    return job


def start_job(db: Session, job: DurableJob, worker_id: str) -> None:
    now = utcnow()
    job.status = "running"
    job.attempts += 1
    job.lease_owner = worker_id
    job.leased_until = now + timedelta(seconds=settings.job_lease_seconds)
    job.started_at = job.started_at or now
    job.error = ""
    record_event(db, job, f"Claimed by {worker_id}")
    db.flush()


def update_progress(db: Session, job: DurableJob, percent: int, message: str = "") -> None:
    if job.status != "running":
        return
    job.progress_percent = max(job.progress_percent, min(99, max(0, percent)))
    job.leased_until = utcnow() + timedelta(seconds=settings.job_lease_seconds)
    record_event(db, job, message or "Progress updated")


def complete_job(db: Session, job: DurableJob, result: dict[str, Any] | None = None) -> None:
    if job.cancellation_requested:
        job.status = "cancelled"
        job.lease_owner = ""
        job.leased_until = None
        job.completed_at = utcnow()
        record_event(db, job, "Cancellation acknowledged by worker")
        return
    job.status = "completed"
    job.progress_percent = 100
    job.result = result or {}
    job.error = ""
    job.lease_owner = ""
    job.leased_until = None
    job.completed_at = utcnow()
    record_event(db, job, "Job completed")


def fail_job(db: Session, job: DurableJob, error: str) -> None:
    now = utcnow()
    job.error = error[-4000:]
    job.lease_owner = ""
    job.leased_until = None
    if job.cancellation_requested:
        job.status = "cancelled"
        job.completed_at = now
        record_event(db, job, "Job cancelled")
    elif job.attempts < job.max_attempts:
        job.status = "queued"
        job.next_attempt_at = now + timedelta(seconds=min(300, 2 ** max(0, job.attempts - 1)))
        record_event(db, job, f"Attempt failed; retry {job.attempts + 1} scheduled", {"error": job.error})
        notify_job(job)
    else:
        job.status = "failed"
        job.completed_at = now
        record_event(db, job, "Job failed", {"error": job.error})


def request_cancel(db: Session, job: DurableJob) -> DurableJob:
    if job.status in TERMINAL_STATUSES:
        return job
    job.cancellation_requested = True
    if job.status == "queued":
        job.status = "cancelled"
        job.completed_at = utcnow()
        record_event(db, job, "Job cancelled before it started")
    else:
        record_event(db, job, "Cancellation requested")
    return job


def retry_job(db: Session, job: DurableJob) -> DurableJob:
    if job.status not in {"failed", "cancelled"}:
        return job
    job.status = "queued"
    job.progress_percent = 0
    job.attempts = 0
    job.error = ""
    job.result = {}
    job.cancellation_requested = False
    job.next_attempt_at = utcnow()
    job.completed_at = None
    record_event(db, job, "Job manually returned to queue")
    notify_job(job)
    return job


def event_dict(event: DurableJobEvent) -> dict[str, Any]:
    return {
        "id": event.id,
        "status": event.status,
        "progress_percent": event.progress_percent,
        "message": event.message,
        "data": event.event_data,
        "created_at": event.created_at,
    }
