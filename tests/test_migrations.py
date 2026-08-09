from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.orm import Session

from app.database import Base
from app.models import Project
from app.schema_migrations import database_revision, expected_revision, migrate_database


def sqlite_engine(path):
    return create_engine(f"sqlite:///{path.as_posix()}", connect_args={"check_same_thread": False})


@pytest.fixture
def migration_db_path():
    root = Path("work/test-migrations")
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{uuid4().hex}.db"
    yield path
    for candidate in [path, Path(f"{path}-journal"), Path(f"{path}-wal"), Path(f"{path}-shm")]:
        if candidate.exists(): candidate.unlink()


def test_blank_database_upgrades_to_current_schema(migration_db_path):
    engine = sqlite_engine(migration_db_path)
    try:
        revision = migrate_database(engine)
        tables = set(inspect(engine).get_table_names())
        assert revision == expected_revision() == database_revision(engine)
        assert {"alembic_version", "projects", "compliance_scans", "professional_identities"}.issubset(tables)
        assert migrate_database(engine) == revision
    finally:
        engine.dispose()


def test_existing_create_all_database_is_adopted_without_losing_data(migration_db_path):
    engine = sqlite_engine(migration_db_path)
    try:
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            db.add(Project(title="Preserved Production", logline="This row must survive migration adoption."))
            db.commit()
        assert database_revision(engine) == "legacy"
        assert migrate_database(engine) == expected_revision()
        with Session(engine) as db:
            assert db.scalar(select(Project.title)) == "Preserved Production"
    finally:
        engine.dispose()


def test_incomplete_legacy_database_is_not_silently_stamped(migration_db_path):
    engine = sqlite_engine(migration_db_path)
    try:
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE projects (id INTEGER PRIMARY KEY)"))
        try:
            migrate_database(engine)
        except RuntimeError as exc:
            assert "projects" in str(exc) and "required columns are missing" in str(exc)
        else:
            raise AssertionError("An incomplete legacy schema must not be stamped as current")
        assert database_revision(engine) == "legacy"
    finally:
        engine.dispose()
