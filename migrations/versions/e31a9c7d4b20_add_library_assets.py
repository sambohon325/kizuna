"""add unified library assets

Revision ID: e31a9c7d4b20
Revises: 9f3a7b1c5d20
Create Date: 2026-08-10
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e31a9c7d4b20"
down_revision: Union[str, Sequence[str], None] = "9f3a7b1c5d20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "library_assets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("group_key", sa.String(length=64), nullable=False),
        sa.Column("category", sa.String(length=48), nullable=False, server_default="reference"),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("tags", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("uri", sa.Text(), nullable=False),
        sa.Column("mime_type", sa.String(length=80), nullable=False, server_default="application/octet-stream"),
        sa.Column("rights_status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("rights_notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("source_tool", sa.String(length=80), nullable=False, server_default="creator upload"),
        sa.Column("asset_metadata", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_library_assets_group_key", "library_assets", ["group_key"])
    op.create_index("ix_library_assets_project_category", "library_assets", ["project_id", "category"])


def downgrade() -> None:
    op.drop_index("ix_library_assets_project_category", table_name="library_assets")
    op.drop_index("ix_library_assets_group_key", table_name="library_assets")
    op.drop_table("library_assets")
