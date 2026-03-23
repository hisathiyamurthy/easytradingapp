"""Alembic script template."""
from alembic import context as alembic_context
from alembic.operations import ops

revision = alembic_context.revision
down_revision = alembic_context.down_revision or None
branch_labels = alembic_context.branch_labels
depends_on = alembic_context.depends_on


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
