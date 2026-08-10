"""expand crew agent profiles

Revision ID: c28e5d9a731f
Revises: 7a9d11b246c8
Create Date: 2026-08-09
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c28e5d9a731f"
down_revision: Union[str, Sequence[str], None] = "7a9d11b246c8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("crew_assignments", sa.Column("traits", sa.JSON(), nullable=False, server_default="[]"))
    op.add_column("crew_assignments", sa.Column("provider_key", sa.String(length=120), nullable=False, server_default="auto"))
    op.add_column("crew_assignments", sa.Column("model_override", sa.String(length=255), nullable=False, server_default=""))


def downgrade() -> None:
    op.drop_column("crew_assignments", "model_override")
    op.drop_column("crew_assignments", "provider_key")
    op.drop_column("crew_assignments", "traits")
