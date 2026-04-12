"""Initial schema — baseline for existing tables

Revision ID: 0001
Revises:
Create Date: 2026-04-11

This migration represents the schema that was previously managed by
SQLAlchemy's auto-create. Marking it as the baseline so future
migrations can build on top of it.
On an existing database run:  alembic stamp 0001
On a fresh database run:      alembic upgrade head
"""
from typing import Sequence, Union

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Existing tables are created by SQLAlchemy auto-create on startup.
    # This migration is intentionally a no-op — it just establishes the
    # baseline revision so subsequent migrations can track diffs correctly.
    pass


def downgrade() -> None:
    pass
