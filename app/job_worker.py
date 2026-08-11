from __future__ import annotations

import os
import socket
import time
import logging
from uuid import uuid4

from app.config import settings
from app.database import SessionLocal
from app.job_queue import claim_job, complete_job, fail_job, redis_client, update_progress, wait_for_notification
from app.media_proxy import execute_media_proxy_job
from app.storage_maintenance import execute_storage_audit_job
from app.main import execute_composite_render_job, execute_crew_proposal_job, execute_crew_voice_job, execute_master_assembly_job, execute_project_backup_job, execute_shot_motion_render_job, execute_timeline_render_job, mark_composite_render_job_failed, mark_crew_job_failed, mark_master_assembly_job_failed, mark_project_backup_failed, mark_shot_motion_job_failed, mark_timeline_render_job_failed
from app.schema_migrations import migrate_database
from app.observability import ServiceHeartbeatLoop, log_event, service_logger


HANDLERS = {"media.proxy": execute_media_proxy_job, "maintenance.storage-audit": execute_storage_audit_job, "maintenance.backup": execute_project_backup_job, "crew.proposal": execute_crew_proposal_job, "crew.voice": execute_crew_voice_job, "render.composite": execute_composite_render_job, "render.shot-motion": execute_shot_motion_render_job, "render.animatic": execute_timeline_render_job, "render.master": execute_timeline_render_job, "render.master-assembly": execute_master_assembly_job}
logger = service_logger("job-worker")


def worker_identity() -> str:
    return f"{socket.gethostname()}:{os.getpid()}:{uuid4().hex[:8]}"


def run_job_once(worker_id: str) -> bool:
    with SessionLocal() as db:
        job = claim_job(db, worker_id, set(HANDLERS))
        db.commit()
        if job is None:
            return False
        job_id = job.id
        log_event(logger, logging.INFO, "job_claimed", "Background job claimed", job_id=job.id, job_kind=job.kind, project_id=job.project_id, worker_id=worker_id)
        try:
            update_progress(db, job, 10, "Preparing working media")
            db.commit()
            result = HANDLERS[job.kind](db, job)
            db.refresh(job)
            complete_job(db, job, result)
            db.commit()
            log_event(logger, logging.INFO, "job_completed", "Background job completed", job_id=job.id, job_kind=job.kind, project_id=job.project_id, worker_id=worker_id)
        except Exception as exc:
            db.rollback()
            job = db.get(type(job), job_id)
            fail_job(db, job, str(exc))
            if job.kind == "maintenance.backup": mark_project_backup_failed(db, job, str(exc))
            elif job.kind in {"crew.proposal", "crew.voice"}: mark_crew_job_failed(db, job, str(exc))
            elif job.kind == "render.shot-motion": mark_shot_motion_job_failed(db, job, str(exc))
            elif job.kind in {"render.animatic", "render.master"}: mark_timeline_render_job_failed(db, job, str(exc))
            elif job.kind == "render.composite": mark_composite_render_job_failed(db, job, str(exc))
            elif job.kind == "render.master-assembly": mark_master_assembly_job_failed(db, job, str(exc))
            db.commit()
            log_event(logger, logging.ERROR, "job_failed", "Background job failed", job_id=job.id, job_kind=job.kind, project_id=job.project_id, worker_id=worker_id, error_type=type(exc).__name__, exc_info=True)
        return True


def main() -> None:
    migrate_database()
    worker_id = worker_identity()
    heartbeat = ServiceHeartbeatLoop("job-worker", details={"worker_id": worker_id, "handlers": sorted(HANDLERS)})
    heartbeat.start()
    log_event(logger, logging.INFO, "service_started", "Background job worker started", worker_id=worker_id, handlers=sorted(HANDLERS))
    stream_id = "$"
    try:
        while True:
            if not run_job_once(worker_id):
                if redis_client() is None:
                    time.sleep(max(0.25, settings.job_poll_seconds))
                else:
                    stream_id = wait_for_notification(stream_id, int(max(0.25, settings.job_poll_seconds) * 1000))
    finally:
        heartbeat.stop()
        log_event(logger, logging.INFO, "service_stopped", "Background job worker stopped", worker_id=worker_id)


if __name__ == "__main__":
    main()
