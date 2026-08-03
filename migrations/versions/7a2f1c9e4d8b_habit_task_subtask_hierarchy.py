"""habit/task/subtask hierarchy, archive-friendly log

Revision ID: 7a2f1c9e4d8b
Revises: 5c88d9a93f41
Create Date: 2026-08-03 00:00:00.000000

"""
from datetime import date

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '7a2f1c9e4d8b'
down_revision = '5c88d9a93f41'
branch_labels = None
depends_on = None

PALETTE = ["#e8ff6b", "#6bffd4", "#ff6b9d", "#6bb1ff", "#ffb06b", "#b06bff", "#6bffb0", "#ff8a6b"]


def upgrade():
    bind = op.get_bind()

    op.create_table('habit',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('color', sa.String(length=7), nullable=True),
        sa.Column('created_on', sa.Date(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('removed_on', sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table('subtask',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('frequency', sa.Integer(), nullable=True),
        sa.Column('created_on', sa.Date(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('removed_on', sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(['task_id'], ['task.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )

    op.add_column('task', sa.Column('habit_id', sa.Integer(), nullable=True))

    # ── data migration: one Habit per distinct (user_id, type), colors cycled per user ──
    rows = bind.execute(sa.text(
        "SELECT user_id, type, MIN(created_on) AS earliest "
        "FROM task GROUP BY user_id, type"
    )).fetchall()

    habit_ids = {}  # (user_id, type) -> habit_id
    color_idx_by_user = {}
    for row in rows:
        idx = color_idx_by_user.get(row.user_id, 0)
        color = PALETTE[idx % len(PALETTE)]
        color_idx_by_user[row.user_id] = idx + 1

        result = bind.execute(sa.text(
            "INSERT INTO habit (user_id, name, description, color, created_on, is_active) "
            "VALUES (:user_id, :name, '', :color, :created_on, true) RETURNING id"
        ), {
            "user_id": row.user_id,
            "name": row.type or "Uncategorized",
            "color": color,
            "created_on": row.earliest or date.today(),
        }).fetchone()
        habit_ids[(row.user_id, row.type)] = result.id

    for (user_id, typ), habit_id in habit_ids.items():
        if typ is None:
            bind.execute(sa.text(
                "UPDATE task SET habit_id = :habit_id WHERE user_id = :user_id AND type IS NULL"
            ), {"habit_id": habit_id, "user_id": user_id})
        else:
            bind.execute(sa.text(
                "UPDATE task SET habit_id = :habit_id WHERE user_id = :user_id AND type = :type"
            ), {"habit_id": habit_id, "user_id": user_id, "type": typ})

    op.alter_column('task', 'habit_id', nullable=False)
    op.create_foreign_key('fk_task_habit', 'task', 'habit', ['habit_id'], ['id'])

    # ── convert non-empty free-text subtask field into real Subtask rows ──
    tasks_with_subtask = bind.execute(sa.text(
        "SELECT id, subtask, frequency, created_on FROM task "
        "WHERE subtask IS NOT NULL AND subtask <> ''"
    )).fetchall()
    for t in tasks_with_subtask:
        bind.execute(sa.text(
            "INSERT INTO subtask (task_id, name, description, frequency, created_on, is_active) "
            "VALUES (:task_id, :name, '', :frequency, :created_on, true)"
        ), {
            "task_id": t.id,
            "name": t.subtask,
            "frequency": t.frequency or 1,
            "created_on": t.created_on or date.today(),
        })

    op.drop_column('task', 'type')
    op.drop_column('task', 'subtask')
    op.drop_column('task', 'parent_id')

    # ── log: allow task_id OR subtask_id ──
    op.add_column('log', sa.Column('subtask_id', sa.Integer(), nullable=True))
    op.alter_column('log', 'task_id', nullable=True)
    op.drop_constraint('uq_log_entry', 'log', type_='unique')
    op.create_index(
        'uq_log_task_entry', 'log', ['user_id', 'date', 'task_id', 'occurrence'],
        unique=True, postgresql_where=sa.text('subtask_id IS NULL'),
    )
    op.create_index(
        'uq_log_subtask_entry', 'log', ['user_id', 'date', 'subtask_id', 'occurrence'],
        unique=True, postgresql_where=sa.text('task_id IS NULL'),
    )


def downgrade():
    op.drop_index('uq_log_subtask_entry', table_name='log')
    op.drop_index('uq_log_task_entry', table_name='log')
    op.create_unique_constraint('uq_log_entry', 'log', ['user_id', 'date', 'task_id', 'occurrence'])
    op.alter_column('log', 'task_id', nullable=False)
    op.drop_column('log', 'subtask_id')

    op.add_column('task', sa.Column('type', sa.String(length=120), nullable=True))
    op.add_column('task', sa.Column('subtask', sa.String(length=255), nullable=True))
    op.add_column('task', sa.Column('parent_id', sa.Integer(), nullable=True))

    bind = op.get_bind()
    bind.execute(sa.text(
        "UPDATE task SET type = habit.name FROM habit WHERE task.habit_id = habit.id"
    ))

    op.drop_constraint('fk_task_habit', 'task', type_='foreignkey')
    op.drop_column('task', 'habit_id')

    op.drop_table('subtask')
    op.drop_table('habit')
