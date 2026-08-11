# Database migrations

Kizuna uses Alembic to version its SQLite and PostgreSQL schemas. The web process and durable job worker apply pending migrations before doing production work. Docker Compose and Coolify additionally run a dedicated one-shot `migrate` service; web, worker, and backup services wait for it to succeed.

## Local development

Normal startup is enough:

```powershell
uvicorn app.main:app --reload
```

To migrate without starting the browser application:

```powershell
python -m app.schema_migrations
```

The health response reports the active `database_revision`. To confirm the models and migration head agree:

```powershell
python -m alembic check
```

Startup also validates that a database marked at the current revision still contains every required table and column. A revision marker cannot silently hide a partially removed schema.

## Existing Kizuna databases

The first migration-aware startup recognizes an existing database with Kizuna's `projects` table but no Alembic version record. It creates only currently missing tables, verifies that every existing table contains all required baseline columns, preserves data, and then stamps the baseline revision.

If an existing table is missing required columns, startup stops with an explicit error instead of stamping or guessing. Back up the database and add a reviewed bridge migration before continuing. Kizuna never runs destructive downgrade operations automatically.

## Adding a schema change

1. Change the SQLAlchemy model.
2. Generate a revision with `python -m alembic revision --autogenerate -m "describe the change"`.
3. Review both `upgrade()` and `downgrade()` carefully, including data backfills and PostgreSQL behavior.
4. Run `python -m alembic check` and the full test suite.
5. Test the upgrade against a copy of production data before deployment.

Autogeneration is a draft, not approval. Renames, non-null columns, type changes, large-table operations, and data migrations require deliberate migration code.

## Coolify and Docker Compose

The image contains `alembic.ini` and the complete `migrations/` directory. The `migrate` service waits for PostgreSQL, acquires a PostgreSQL advisory lock, upgrades to the current head, and exits successfully. Application services start only after that exit.

Before deploying a new migration:

- create and verify a database backup;
- review the generated SQL and expected lock time;
- use expand/backfill/contract changes for large or zero-downtime deployments;
- confirm sufficient storage for table rewrites and indexes; and
- keep the previous application image available for application rollback.

Application rollback does not imply database downgrade. Prefer forward fixes; run a downgrade only after reviewing its data-loss implications.

## PostgreSQL CI proof

GitHub Actions migrates a fresh PostgreSQL service, runs Alembic structural drift detection, and executes `python -m app.database_verification` before and after the full test suite. The verifier requires PostgreSQL, confirms the current revision and complete table set, performs a nested JSON write/read transaction, and rolls that transaction back. SQLite remains the fast local-development and compatibility test path.

Alembic compares tables, columns, types, constraints, and indexes. Database bootstrap defaults are intentionally excluded because many Kizuna models use Python-side defaults while migrations retain database-side defaults for safe historical upgrades.
