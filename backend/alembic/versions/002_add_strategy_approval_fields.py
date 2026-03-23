"""Add approval fields to strategies.

Revision ID: 002_add_strategy_approval_fields
Revises: 001_add_strategy_instances
Create Date: 2026-03-21

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '002_add_strategy_approval_fields'
down_revision = '001_add_strategy_instances'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('strategies', sa.Column('approved', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('strategies', sa.Column('approved_by', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('strategies', sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key('fk_strategy_approved_by', 'strategies', 'users', ['approved_by'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    op.drop_constraint('fk_strategy_approved_by', 'strategies', type_='foreignkey')
    op.drop_column('strategies', 'approved_at')
    op.drop_column('strategies', 'approved_by')
    op.drop_column('strategies', 'approved')
