"""Link timeline renders to the durable job ledger.

Revision ID: d96f2b5e7a84
Revises: c85e1a4d6f73
"""

from alembic import op
import sqlalchemy as sa


revision = "d96f2b5e7a84"
down_revision = "c85e1a4d6f73"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("animatic_renders") as batch:
        batch.add_column(sa.Column("durable_job_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_animatic_render_durable_job", "durable_jobs", ["durable_job_id"], ["id"])
        batch.create_unique_constraint("uq_animatic_render_durable_job", ["durable_job_id"])


def downgrade() -> None:
    with op.batch_alter_table("animatic_renders") as batch:
        batch.drop_constraint("uq_animatic_render_durable_job", type_="unique")
        batch.drop_constraint("fk_animatic_render_durable_job", type_="foreignkey")
        batch.drop_column("durable_job_id")
