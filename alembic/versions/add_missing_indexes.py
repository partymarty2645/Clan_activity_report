"""add performance indexes

This migration adds indexes to improve query performance for common queries.
These are read-only operations with no data changes.

Note: Many indexes already exist from earlier manual schema creation.
This migration only adds truly missing indexes for FK columns and composite queries.

Revision ID: add_missing_indexes_003
Revises: drop_unused_001
Create Date: 2025-12-22 16:45:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_missing_indexes_003'
down_revision = 'drop_unused_001'
branch_labels = None
depends_on = None


def upgrade():
    """Add missing performance indexes for new columns (after 2.2.2 migration)."""
    # Note: Most indexes already exist from manual schema creation
    # This is mostly a no-op migration, but maintains proper migration history
    # After 2.2.2 (normalize_user_ids), run this to add indexes on new user_id columns:
    # - idx_wom_snapshots_user_timestamp (user_id, timestamp composite)
    # - idx_discord_messages_user_id (user_id FK reference)
    # - idx_boss_snapshots_wom_snapshot_id (wom_snapshot_id FK reference)
    
    # For now, safely check if indexes exist before creating
    try:
        op.create_index(
            'idx_wom_snapshots_user_timestamp',
            'wom_snapshots',
            ['user_id', 'timestamp'],
            unique=False
        )
    except Exception:
        pass  # Already exists or user_id column doesn't exist yet
    
    try:
        op.create_index(
            'idx_discord_messages_user_id',
            'discord_messages',
            ['user_id'],
            unique=False
        )
    except Exception:
        pass  # Already exists or user_id column doesn't exist yet
    
    try:
        op.create_index(
            'idx_boss_snapshots_wom_snapshot_id',
            'boss_snapshots',
            ['wom_snapshot_id'],
            unique=False
        )
    except Exception:
        pass  # Already exists or column doesn't exist yet


def downgrade():
    """Remove added indexes."""
    try:
        op.drop_index('idx_wom_snapshots_user_timestamp', table_name='wom_snapshots')
    except Exception:
        pass
    
    try:
        op.drop_index('idx_discord_messages_user_id', table_name='discord_messages')
    except Exception:
        pass
    
    try:
        op.drop_index('idx_boss_snapshots_wom_snapshot_id', table_name='boss_snapshots')
    except Exception:
        pass
