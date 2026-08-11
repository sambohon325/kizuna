from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import Engine, inspect, text

from app.database import Base, engine as default_engine
import app.models  # noqa: F401 -- registers all tables before legacy validation


MIGRATION_LOCK_ID = 4_912_026_080_900


def migration_config() -> Config:
    root = Path(__file__).resolve().parent.parent
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "migrations"))
    return config


def expected_revision() -> str:
    return ScriptDirectory.from_config(migration_config()).get_current_head() or ""


def database_revision(target_engine: Engine = default_engine) -> str:
    with target_engine.connect() as connection:
        tables = set(inspect(connection).get_table_names())
        if "alembic_version" not in tables:
            return "legacy" if "projects" in tables else "uninitialized"
        return MigrationContext.configure(connection).get_current_revision() or ""


def _validate_legacy_schema(connection) -> None:
    inspector = inspect(connection)
    existing_tables = set(inspector.get_table_names())
    Base.metadata.create_all(bind=connection, checkfirst=True)
    connection.commit()
    inspector = inspect(connection)
    problems = []
    for table in Base.metadata.sorted_tables:
        if table.name not in existing_tables:
            continue
        actual_columns = {item["name"] for item in inspector.get_columns(table.name)}
        missing = set(table.columns.keys()) - actual_columns
        if missing:
            problems.append(f"{table.name}: {', '.join(sorted(missing))}")
    if problems:
        raise RuntimeError("Legacy database cannot be safely adopted because required columns are missing: " + "; ".join(problems))


def _validate_current_schema(connection) -> None:
    inspector = inspect(connection)
    existing_tables = set(inspector.get_table_names())
    missing_tables = sorted(set(Base.metadata.tables) - existing_tables)
    if missing_tables:
        raise RuntimeError("Database revision is current but required tables are missing: " + ", ".join(missing_tables))
    problems = []
    for table in Base.metadata.sorted_tables:
        actual_columns = {item["name"] for item in inspector.get_columns(table.name)}
        missing = set(table.columns.keys()) - actual_columns
        if missing:
            problems.append(f"{table.name}: {', '.join(sorted(missing))}")
    if problems:
        raise RuntimeError("Database revision is current but required columns are missing: " + "; ".join(problems))


def migrate_database(target_engine: Engine = default_engine) -> str:
    config = migration_config()
    with target_engine.connect() as connection:
        postgres = connection.dialect.name == "postgresql"
        if postgres:
            connection.execute(text("SELECT pg_advisory_lock(:lock_id)"), {"lock_id": MIGRATION_LOCK_ID})
            connection.commit()
        try:
            tables = set(inspect(connection).get_table_names())
            config.attributes["connection"] = connection
            if "alembic_version" not in tables and "projects" in tables:
                _validate_legacy_schema(connection)
                command.stamp(config, "head")
            else:
                command.upgrade(config, "head")
            connection.commit()
            _validate_current_schema(connection)
            return MigrationContext.configure(connection).get_current_revision() or expected_revision()
        finally:
            if postgres:
                connection.execute(text("SELECT pg_advisory_unlock(:lock_id)"), {"lock_id": MIGRATION_LOCK_ID})
                connection.commit()


def main() -> None:
    revision = migrate_database()
    print(f"Kizuna database is ready at revision {revision}", flush=True)


if __name__ == "__main__":
    main()
