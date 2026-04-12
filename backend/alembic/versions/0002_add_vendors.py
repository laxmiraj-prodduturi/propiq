"""Add vendors table

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-11
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "vendors",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("tenant_id", sa.String(50), sa.ForeignKey("tenant_orgs.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("trade", sa.String(100), nullable=False),
        sa.Column("email", sa.String(255), server_default=""),
        sa.Column("phone", sa.String(50), server_default=""),
        sa.Column("rating", sa.Float, server_default="0"),
        sa.Column("response_time", sa.String(50), server_default=""),
        sa.Column("is_active", sa.Boolean, server_default="1"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("vendors")
