"""add todo table

Revision ID: 9b1e3a7c2f5d
Revises: 7a2f1c9e4d8b
Create Date: 2026-08-04 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '9b1e3a7c2f5d'
down_revision = '7a2f1c9e4d8b'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('to_do',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('deadline', sa.Date(), nullable=True),
        sa.Column('created_on', sa.Date(), nullable=False),
        sa.Column('is_done', sa.Boolean(), nullable=True),
        sa.Column('completed_on', sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade():
    op.drop_table('to_do')
