"""add beta invitations

Revision ID: a91c2e4f7b30
Revises: 6f2c7a84b1d9
Create Date: 2026-08-12
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a91c2e4f7b30"
down_revision: Union[str, Sequence[str], None] = "6f2c7a84b1d9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "beta_invitations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_request_id", sa.String(length=80), nullable=False),
        sa.Column("source_application_id", sa.String(length=80), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("display_name", sa.String(length=160), nullable=False),
        sa.Column("experience", sa.String(length=32), nullable=False),
        sa.Column("creator_type", sa.String(length=80), nullable=False),
        sa.Column("cohort", sa.String(length=80), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("access_ends_at", sa.DateTime(), nullable=False),
        sa.Column("accepted_at", sa.DateTime(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_request_id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_beta_invitations_source_application_id", "beta_invitations", ["source_application_id"])
    op.create_index("ix_beta_invitations_email", "beta_invitations", ["email"])


def downgrade() -> None:
    op.drop_index("ix_beta_invitations_email", table_name="beta_invitations")
    op.drop_index("ix_beta_invitations_source_application_id", table_name="beta_invitations")
    op.drop_table("beta_invitations")
