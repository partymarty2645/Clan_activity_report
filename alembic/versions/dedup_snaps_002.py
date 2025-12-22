"""deduplicate snapshots

Revision ID: dedup_snaps_002
Revises: add_indexes_001
Create Date: 2025-12-22 01:00:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'dedup_snaps_002'
down_revision = 'add_indexes_001'
branch_labels = None
depends_on = None

def upgrade():
    # 1. Drop the non-unique index if it exists (created in previous migration)
    # Note: SQLite doesn't support DROP INDEX IF EXISTS in older versions, but Alembic might handle it.
    # We'll try to drop it.
    try:
        op.drop_index('idx_wom_snapshots_username_timestamp', table_name='wom_snapshots')
    except Exception:
        pass # Index might not exist or name differs

    # 2. Add Unique Constraint (via unique index)
    # This ensures (username, timestamp) is unique
    with op.batch_alter_table('wom_snapshots') as batch_op:
        batch_op.create_index('uq_wom_snapshots_user_ts', ['username', 'timestamp'], unique=True)


def downgrade():
    try:
        op.drop_index('uq_wom_snapshots_user_ts', table_name='wom_snapshots')
    except:
        pass
    
    # Restore non-unique index
    op.create_index('idx_wom_snapshots_username_timestamp', 'wom_snapshots', ['username', 'timestamp'])
