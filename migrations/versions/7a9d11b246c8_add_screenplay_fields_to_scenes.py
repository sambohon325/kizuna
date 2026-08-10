"""add screenplay fields to scenes

Revision ID: 7a9d11b246c8
Revises: f14c0b7a921e
Create Date: 2026-08-09
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7a9d11b246c8"
down_revision: Union[str, Sequence[str], None] = "f14c0b7a921e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("scenes", sa.Column("slugline", sa.String(length=255), nullable=False, server_default=""))
    op.add_column("scenes", sa.Column("script", sa.Text(), nullable=False, server_default=""))
    op.add_column("scenes", sa.Column("notes", sa.Text(), nullable=False, server_default=""))
    op.add_column("scenes", sa.Column("draft_status", sa.String(length=32), nullable=False, server_default="outline"))


def downgrade() -> None:
    op.drop_column("scenes", "draft_status")
    op.drop_column("scenes", "notes")
    op.drop_column("scenes", "script")
    op.drop_column("scenes", "slugline")
