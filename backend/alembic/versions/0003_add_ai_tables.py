"""Add AI session, message and approval tables

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-11
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_sessions",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("tenant_id", sa.String(50), sa.ForeignKey("tenant_orgs.id"), nullable=False),
        sa.Column("user_id", sa.String(50), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("session_id", sa.String(100), unique=True, nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("last_active_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "ai_messages",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("session_id", sa.String(100), sa.ForeignKey("ai_sessions.session_id"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("action_card_json", sa.Text),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "ai_approvals",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("tenant_id", sa.String(50), sa.ForeignKey("tenant_orgs.id"), nullable=False),
        sa.Column("user_id", sa.String(50), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("session_id", sa.String(100), sa.ForeignKey("ai_sessions.session_id"), nullable=False),
        sa.Column("action_id", sa.String(50), unique=True, nullable=False),
        sa.Column("action_type", sa.String(100), nullable=False),
        sa.Column("action_payload_json", sa.Text),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("approver_user_id", sa.String(50)),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime),
    )


def downgrade() -> None:
    op.drop_table("ai_approvals")
    op.drop_table("ai_messages")
    op.drop_table("ai_sessions")
