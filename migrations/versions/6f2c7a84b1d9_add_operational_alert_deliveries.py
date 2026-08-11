"""add operational alert delivery history

Revision ID: 6f2c7a84b1d9
Revises: 5e8b2a91c4d7
Create Date: 2026-08-11
"""

from alembic import op
import sqlalchemy as sa


revision = "6f2c7a84b1d9"
down_revision = "5e8b2a91c4d7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "operational_alert_deliveries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("channel", sa.String(length=24), nullable=False),
        sa.Column("alert_key", sa.String(length=80), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="pending"),
        sa.Column("target_hint", sa.String(length=160), nullable=False, server_default=""),
        sa.Column("payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("response_code", sa.Integer(), nullable=True),
        sa.Column("error", sa.Text(), nullable=False, server_default=""),
        sa.Column("delivered_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_operational_alert_delivery_lookup", "operational_alert_deliveries", ["channel", "fingerprint", "created_at"])
    op.create_index("ix_operational_alert_delivery_created", "operational_alert_deliveries", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_operational_alert_delivery_created", table_name="operational_alert_deliveries")
    op.drop_index("ix_operational_alert_delivery_lookup", table_name="operational_alert_deliveries")
    op.drop_table("operational_alert_deliveries")
