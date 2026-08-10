"""Link project backups to the durable job ledger.

Revision ID: a63c9e8b2d41
Revises: f42b8d6e1c30
"""

from alembic import op
import sqlalchemy as sa


revision = "a63c9e8b2d41"
down_revision = "f42b8d6e1c30"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("project_backups") as batch:
        batch.add_column(sa.Column("durable_job_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_project_backup_durable_job", "durable_jobs", ["durable_job_id"], ["id"])
        batch.create_unique_constraint("uq_project_backup_durable_job", ["durable_job_id"])


def downgrade() -> None:
    with op.batch_alter_table("project_backups") as batch:
        batch.drop_constraint("uq_project_backup_durable_job", type_="unique")
        batch.drop_constraint("fk_project_backup_durable_job", type_="foreignkey")
        batch.drop_column("durable_job_id")
