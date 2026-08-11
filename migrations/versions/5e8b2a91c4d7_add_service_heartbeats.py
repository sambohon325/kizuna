"""add service heartbeats

Revision ID: 5e8b2a91c4d7
Revises: d41f08c7a2be
Create Date: 2026-08-11
"""

from alembic import op
import sqlalchemy as sa


revision = "5e8b2a91c4d7"
down_revision = "d41f08c7a2be"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "service_heartbeats",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("service_key", sa.String(length=64), nullable=False),
        sa.Column("instance_id", sa.String(length=160), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="ready"),
        sa.Column("details", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("started_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("last_seen", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("service_key", "instance_id", name="uq_service_heartbeat_instance"),
    )
    op.create_index("ix_service_heartbeats_service_last_seen", "service_heartbeats", ["service_key", "last_seen"])


def downgrade() -> None:
    op.drop_index("ix_service_heartbeats_service_last_seen", table_name="service_heartbeats")
    op.drop_table("service_heartbeats")
