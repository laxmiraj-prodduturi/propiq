"""Add tenant_id and file_path to documents table

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-11
"""

from alembic import op
import sqlalchemy as sa

revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('documents', sa.Column('tenant_id', sa.String(50), nullable=True, server_default='t1'))
    op.add_column('documents', sa.Column('file_path', sa.String(1000), nullable=True, server_default=''))


def downgrade() -> None:
    op.drop_column('documents', 'file_path')
    op.drop_column('documents', 'tenant_id')
