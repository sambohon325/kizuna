"""Link shot motion renders to the durable job ledger.

Revision ID: c85e1a4d6f73
Revises: b74d0f9c3e52
"""

from alembic import op
import sqlalchemy as sa


revision = "c85e1a4d6f73"
down_revision = "b74d0f9c3e52"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("shot_motion_renders") as batch:
        batch.add_column(sa.Column("durable_job_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_shot_motion_render_durable_job", "durable_jobs", ["durable_job_id"], ["id"])
        batch.create_unique_constraint("uq_shot_motion_render_durable_job", ["durable_job_id"])


def downgrade() -> None:
    with op.batch_alter_table("shot_motion_renders") as batch:
        batch.drop_constraint("uq_shot_motion_render_durable_job", type_="unique")
        batch.drop_constraint("fk_shot_motion_render_durable_job", type_="foreignkey")
        batch.drop_column("durable_job_id")
