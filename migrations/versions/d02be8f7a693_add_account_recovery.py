"""add account recovery

Revision ID: d02be8f7a693
Revises: 82a7ef31d0c4
Create Date: 2026-08-09
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d02be8f7a693"
down_revision: Union[str, Sequence[str], None] = "82a7ef31d0c4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("email_verified_at", sa.DateTime(), nullable=True))
    op.execute("UPDATE users SET email_verified_at = CURRENT_TIMESTAMP")
    op.create_table(
        "account_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("purpose", sa.String(length=32), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_account_tokens_user_purpose", "account_tokens", ["user_id", "purpose"])
    op.create_table(
        "account_security_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("network_hash", sa.String(length=64), nullable=False),
        sa.Column("event_metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_account_security_events_network_time", "account_security_events", ["network_hash", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_account_security_events_network_time", table_name="account_security_events")
    op.drop_table("account_security_events")
    op.drop_index("ix_account_tokens_user_purpose", table_name="account_tokens")
    op.drop_table("account_tokens")
    with op.batch_alter_table("users") as batch:
        batch.drop_column("email_verified_at")
