"""add trial entitlements

Revision ID: 82a7ef31d0c4
Revises: 4c9f4bea1172
Create Date: 2026-08-09
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "82a7ef31d0c4"
down_revision: Union[str, Sequence[str], None] = "4c9f4bea1172"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("account_tier", sa.String(length=32), nullable=False, server_default="studio"))
        batch.add_column(sa.Column("trial_ends_at", sa.DateTime(), nullable=True))
    with op.batch_alter_table("master_export_jobs") as batch:
        batch.add_column(sa.Column("watermarked", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.add_column(sa.Column("max_duration_seconds", sa.Float(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("master_export_jobs") as batch:
        batch.drop_column("max_duration_seconds")
        batch.drop_column("watermarked")
    with op.batch_alter_table("users") as batch:
        batch.drop_column("trial_ends_at")
        batch.drop_column("account_tier")
