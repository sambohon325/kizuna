"""Production-database verification used by CI after Alembic migrations."""

from __future__ import annotations

import json
from uuid import uuid4

from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from app.database import Base, engine
from app.models import DurableJob, Project, ServiceHeartbeat
from app.schema_migrations import database_revision, expected_revision


def verify_postgres_database() -> dict:
    if engine.dialect.name != "postgresql":
        raise RuntimeError(f"PostgreSQL verification requires PostgreSQL, not {engine.dialect.name}.")
    revision = database_revision(engine)
    expected = expected_revision()
    if revision != expected:
        raise RuntimeError(f"Database revision {revision!r} does not match migration head {expected!r}.")
    tables = set(inspect(engine).get_table_names())
    required = set(Base.metadata.tables)
    missing = sorted(required - tables)
    if missing:
        raise RuntimeError(f"Migrated PostgreSQL schema is missing tables: {', '.join(missing)}")

    token = uuid4().hex
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            with Session(bind=connection, autoflush=False, expire_on_commit=False) as db:
                project = Project(title=f"PostgreSQL verification {token[:8]}", logline="This transaction is rolled back.")
                db.add(project)
                db.flush()
                job = DurableJob(job_key=token, project_id=project.id, kind="ci.database-verification", payload={"database": "postgresql", "nested": {"json": True}}, result={})
                heartbeat = ServiceHeartbeat(service_key="ci-verifier", instance_id=token, details={"transaction": "rollback"})
                db.add_all([job, heartbeat])
                db.flush()
                stored = db.scalar(select(DurableJob).where(DurableJob.job_key == token))
                if stored is None or stored.payload.get("nested", {}).get("json") is not True:
                    raise RuntimeError("PostgreSQL JSON transaction round-trip failed.")
        finally:
            transaction.rollback()
    return {"verified": True, "dialect": engine.dialect.name, "revision": revision, "tables": len(required), "transaction_rolled_back": True}


def main() -> None:
    print(json.dumps(verify_postgres_database(), sort_keys=True))


if __name__ == "__main__":
    main()
