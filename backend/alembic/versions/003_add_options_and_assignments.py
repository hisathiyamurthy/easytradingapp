"""Add columns for options trading and user assignments.

Revision ID: 003_add_options_and_assignments
Revises: 002_add_strategy_approval_fields
Create Date: 2026-03-23

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '003_add_options_and_assignments'
down_revision = '002_add_strategy_approval_fields'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add options trading columns to orders table
    op.add_column('orders', sa.Column('option_type', sa.String(5), nullable=True))
    op.add_column('orders', sa.Column('strike_price', sa.Float(), nullable=True))
    op.add_column('orders', sa.Column('expiry_date', sa.String(20), nullable=True))
    
    # Create user_strategy_assignments table
    op.create_table(
        'user_strategy_assignments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('strategy_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('assigned_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('deactivated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['strategy_id'], ['strategies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['assigned_by'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_user_strategy_assignments_user_id', 'user_strategy_assignments', ['user_id'])
    op.create_index('ix_user_strategy_assignments_strategy_id', 'user_strategy_assignments', ['strategy_id'])


def downgrade() -> None:
    op.drop_index('ix_user_strategy_assignments_strategy_id', table_name='user_strategy_assignments')
    op.drop_index('ix_user_strategy_assignments_user_id', table_name='user_strategy_assignments')
    op.drop_table('user_strategy_assignments')
    op.drop_column('orders', 'expiry_date')
    op.drop_column('orders', 'strike_price')
    op.drop_column('orders', 'option_type')
