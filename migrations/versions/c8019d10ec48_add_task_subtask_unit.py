"""add unit (day/week/month) to task and subtask

Revision ID: c8019d10ec48
Revises: 9b1e3a7c2f5d
Create Date: 2026-08-04 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'c8019d10ec48'
down_revision = '9b1e3a7c2f5d'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('task', sa.Column('unit', sa.String(length=10), nullable=False, server_default='day'))
    op.add_column('subtask', sa.Column('unit', sa.String(length=10), nullable=False, server_default='day'))
    op.alter_column('task', 'unit', server_default=None)
    op.alter_column('subtask', 'unit', server_default=None)


def downgrade():
    op.drop_column('subtask', 'unit')
    op.drop_column('task', 'unit')
