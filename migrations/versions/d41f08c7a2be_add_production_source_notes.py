"""add production source notes

Revision ID: d41f08c7a2be
Revises: c18b7f4a9d21
Create Date: 2026-08-11
"""

from alembic import op
import sqlalchemy as sa


revision = "d41f08c7a2be"
down_revision = "c18b7f4a9d21"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "production_source_notes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("stage", sa.String(length=32), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("application", sa.Text(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False, server_default=""),
        sa.Column("evidence_refs", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_production_source_notes_project_stage", "production_source_notes", ["project_id", "stage"])


def downgrade() -> None:
    op.drop_index("ix_production_source_notes_project_stage", table_name="production_source_notes")
    op.drop_table("production_source_notes")
