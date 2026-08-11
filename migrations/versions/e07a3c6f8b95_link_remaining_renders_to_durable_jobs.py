"""Link composite and master assembly renders to durable jobs.

Revision ID: e07a3c6f8b95
Revises: d96f2b5e7a84
"""

from alembic import op
import sqlalchemy as sa


revision = "e07a3c6f8b95"
down_revision = "d96f2b5e7a84"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("composite_renders") as batch:
        batch.add_column(sa.Column("durable_job_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_composite_render_durable_job", "durable_jobs", ["durable_job_id"], ["id"])
        batch.create_unique_constraint("uq_composite_render_durable_job", ["durable_job_id"])
    with op.batch_alter_table("master_export_jobs") as batch:
        batch.add_column(sa.Column("durable_job_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_master_export_durable_job", "durable_jobs", ["durable_job_id"], ["id"])
        batch.create_unique_constraint("uq_master_export_durable_job", ["durable_job_id"])


def downgrade() -> None:
    with op.batch_alter_table("master_export_jobs") as batch:
        batch.drop_constraint("uq_master_export_durable_job", type_="unique")
        batch.drop_constraint("fk_master_export_durable_job", type_="foreignkey")
        batch.drop_column("durable_job_id")
    with op.batch_alter_table("composite_renders") as batch:
        batch.drop_constraint("uq_composite_render_durable_job", type_="unique")
        batch.drop_constraint("fk_composite_render_durable_job", type_="foreignkey")
        batch.drop_column("durable_job_id")
