"""link media transfers to durable jobs

Revision ID: f42b8d6e1c30
Revises: e31a9c7d4b20
Create Date: 2026-08-10
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f42b8d6e1c30"
down_revision: Union[str, Sequence[str], None] = "e31a9c7d4b20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("media_transfer_jobs") as batch:
        batch.add_column(sa.Column("durable_job_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_media_transfer_durable_job", "durable_jobs", ["durable_job_id"], ["id"])
        batch.create_unique_constraint("uq_media_transfer_durable_job", ["durable_job_id"])


def downgrade() -> None:
    with op.batch_alter_table("media_transfer_jobs") as batch:
        batch.drop_constraint("uq_media_transfer_durable_job", type_="unique")
        batch.drop_constraint("fk_media_transfer_durable_job", type_="foreignkey")
        batch.drop_column("durable_job_id")
