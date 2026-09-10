"""enable row-level security on user-owned tables

Revision ID: d4e9f7a1b3c6
Revises: c8019d10ec48
Create Date: 2026-08-16 00:00:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = 'd4e9f7a1b3c6'
down_revision = 'c8019d10ec48'
branch_labels = None
depends_on = None

# Tables with a direct user_id column: policy compares it to the session's
# app.current_user_id setting, which the app sets to the logged-in user's id
# at the start of every request (see app.py).
DIRECT_TABLES = ["habit", "task", "to_do", "log"]


def upgrade():
    for table in DIRECT_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY {table}_isolation ON {table}
            USING (user_id = current_setting('app.current_user_id', true)::int)
            WITH CHECK (user_id = current_setting('app.current_user_id', true)::int)
        """)

    # subtask has no user_id of its own; ownership is via its parent task.
    op.execute("ALTER TABLE subtask ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE subtask FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY subtask_isolation ON subtask
        USING (task_id IN (
            SELECT id FROM task WHERE user_id = current_setting('app.current_user_id', true)::int
        ))
        WITH CHECK (task_id IN (
            SELECT id FROM task WHERE user_id = current_setting('app.current_user_id', true)::int
        ))
    """)


def downgrade():
    op.execute("DROP POLICY IF EXISTS subtask_isolation ON subtask")
    op.execute("ALTER TABLE subtask NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE subtask DISABLE ROW LEVEL SECURITY")

    for table in DIRECT_TABLES:
        op.execute(f"DROP POLICY IF EXISTS {table}_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
