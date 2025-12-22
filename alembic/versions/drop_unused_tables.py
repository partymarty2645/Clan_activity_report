"""drop unused snapshot tables

This migration removes the skill_snapshots table which is no longer used
by the analytics pipeline. The activity_snapshots table was never created,
so only skill_snapshots needs to be dropped.

Revision ID: drop_unused_001
Revises: dedup_snaps_002
Create Date: 2025-12-22 10:00:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'drop_unused_001'
down_revision = 'dedup_snaps_002'
branch_labels = None
depends_on = None


def upgrade():
    """Drop skill_snapshots table - no longer used by analytics."""
    # For SQLite compatibility, we need batch_alter_table to drop a table
    # However, dropping a table directly with op.drop_table should work
    try:
        op.drop_table('skill_snapshots')
    except Exception as e:
        # Table might not exist or already dropped
        print(f"Note: Could not drop skill_snapshots table: {e}")
        pass


def downgrade():
    """Recreate skill_snapshots table if migration is rolled back."""
    # Recreate the table with original schema for rollback support
    op.create_table(
        'skill_snapshots',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('snapshot_id', sa.Integer(), nullable=True),
        sa.Column('skill_name', sa.String(), nullable=True),
        sa.Column('xp', sa.Integer(), nullable=True),
        sa.Column('level', sa.Integer(), nullable=True),
        sa.Column('rank', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_skill_snapshots_skill_name', 'skill_name'),
        sa.Index('ix_skill_snapshots_snapshot_id', 'snapshot_id'),
    )
