"""allow creator background assets

Revision ID: 9f3a7b1c5d20
Revises: c28e5d9a731f
Create Date: 2026-08-10
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9f3a7b1c5d20"
down_revision: Union[str, Sequence[str], None] = "c28e5d9a731f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("background_assets") as batch:
        batch.alter_column("background_job_id", existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("background_assets") as batch:
        batch.alter_column("background_job_id", existing_type=sa.Integer(), nullable=False)
