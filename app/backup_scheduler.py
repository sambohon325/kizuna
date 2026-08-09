"""Small single-purpose scheduler process for Coolify and Docker Compose."""

import time

from app.config import settings
from app.database import SessionLocal
from app.main import run_due_backups


def main() -> None:
    interval = max(15, settings.backup_scheduler_interval_seconds)
    while True:
        with SessionLocal() as db:
            result = run_due_backups(db)
            if result["due"]:
                print(f"Backup schedule: {result}", flush=True)
        time.sleep(interval)


if __name__ == "__main__":
    main()
