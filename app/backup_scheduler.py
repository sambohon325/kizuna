"""Small single-purpose scheduler process for Coolify and Docker Compose."""

import logging
import time

from app.config import settings
from app.database import SessionLocal
from app.main import run_due_backups, run_due_restore_drill
from app.observability import ServiceHeartbeatLoop, log_event, service_logger


logger = service_logger("backup-scheduler")


def main() -> None:
    interval = max(15, settings.backup_scheduler_interval_seconds)
    heartbeat = ServiceHeartbeatLoop("backup-scheduler", details={"interval_seconds": interval})
    heartbeat.start()
    log_event(logger, logging.INFO, "service_started", "Backup scheduler started", interval_seconds=interval)
    try:
        while True:
            with SessionLocal() as db:
                result = run_due_backups(db)
                if result["due"]:
                    log_event(logger, logging.INFO, "backup_schedule_checked", "Due backup schedules were queued", **result)
                drill = run_due_restore_drill(db)
                if drill["due"]:
                    log_event(logger, logging.INFO, "restore_drill_scheduled", "A recovery drill was scheduled", **drill)
            time.sleep(interval)
    finally:
        heartbeat.stop()
        log_event(logger, logging.INFO, "service_stopped", "Backup scheduler stopped")


if __name__ == "__main__":
    main()
