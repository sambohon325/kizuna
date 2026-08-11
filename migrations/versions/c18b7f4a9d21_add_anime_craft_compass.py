"""Add the anime craft compass to style profiles.

Revision ID: c18b7f4a9d21
Revises: e07a3c6f8b95
"""

from alembic import op
import sqlalchemy as sa


revision = "c18b7f4a9d21"
down_revision = "e07a3c6f8b95"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("style_profiles") as batch:
        batch.add_column(sa.Column("craft", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))


def downgrade() -> None:
    with op.batch_alter_table("style_profiles") as batch:
        batch.drop_column("craft")
