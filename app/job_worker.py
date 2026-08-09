from __future__ import annotations

import os
import socket
import time
from uuid import uuid4

from app.config import settings
from app.database import SessionLocal
from app.job_queue import claim_job, complete_job, fail_job, redis_client, update_progress, wait_for_notification
from app.media_proxy import execute_media_proxy_job
from app.schema_migrations import migrate_database


HANDLERS = {"media.proxy": execute_media_proxy_job}


def worker_identity() -> str:
    return f"{socket.gethostname()}:{os.getpid()}:{uuid4().hex[:8]}"


def run_job_once(worker_id: str) -> bool:
    with SessionLocal() as db:
        job = claim_job(db, worker_id, set(HANDLERS))
        db.commit()
        if job is None:
            return False
        job_id = job.id
        try:
            update_progress(db, job, 10, "Preparing working media")
            db.commit()
            result = HANDLERS[job.kind](db, job)
            db.refresh(job)
            complete_job(db, job, result)
            db.commit()
        except Exception as exc:
            db.rollback()
            job = db.get(type(job), job_id)
            fail_job(db, job, str(exc))
            db.commit()
        return True


def main() -> None:
    migrate_database()
    worker_id = worker_identity()
    stream_id = "$"
    while True:
        if not run_job_once(worker_id):
            if redis_client() is None:
                time.sleep(max(0.25, settings.job_poll_seconds))
            else:
                stream_id = wait_for_notification(stream_id, int(max(0.25, settings.job_poll_seconds) * 1000))


if __name__ == "__main__":
    main()
