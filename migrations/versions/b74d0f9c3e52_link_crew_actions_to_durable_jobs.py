"""Link AI Crew actions to the durable job ledger.

Revision ID: b74d0f9c3e52
Revises: a63c9e8b2d41
"""

from alembic import op
import sqlalchemy as sa


revision = "b74d0f9c3e52"
down_revision = "a63c9e8b2d41"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("crew_actions") as batch:
        batch.add_column(sa.Column("durable_job_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_crew_action_durable_job", "durable_jobs", ["durable_job_id"], ["id"])
        batch.create_unique_constraint("uq_crew_action_durable_job", ["durable_job_id"])


def downgrade() -> None:
    with op.batch_alter_table("crew_actions") as batch:
        batch.drop_constraint("uq_crew_action_durable_job", type_="unique")
        batch.drop_constraint("fk_crew_action_durable_job", type_="foreignkey")
        batch.drop_column("durable_job_id")
