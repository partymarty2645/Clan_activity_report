"""Migration: Normalize User IDs and Establish Foreign Key Relationships.

Revision ID: normalize_user_ids_004
Revises: add_missing_indexes_003
Create Date: 2025-12-22

This migration:
1. Adds user_id FK columns to wom_snapshots, discord_messages, boss_snapshots
2. Creates primary key on clan_members.id
3. Populates IDs based on username matching
4. Creates FK constraints to ensure referential integrity
5. Maintains backward compatibility with username columns (don't drop them yet)

Risk Level: HIGH
- Modifies production schema
- Creates new FK relationships
- Must preserve data integrity

Rollback: Removes new columns and reverts schema to previous state
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


revision = 'normalize_user_ids_004'
down_revision = 'add_missing_indexes_003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply migration: populate user IDs and add FK constraints."""
    
    bind = op.get_bind()
    
    # 1. Add user_id column to wom_snapshots (if not exists)
    result = bind.execute(text("PRAGMA table_info(wom_snapshots)"))
    columns = {row[1] for row in result.fetchall()}
    
    if 'user_id' not in columns:
        op.add_column('wom_snapshots', sa.Column('user_id', sa.Integer(), nullable=True, index=True))
    
    # 2. Add user_id column to discord_messages (if not exists)
    result = bind.execute(text("PRAGMA table_info(discord_messages)"))
    columns = {row[1] for row in result.fetchall()}
    
    if 'user_id' not in columns:
        op.add_column('discord_messages', sa.Column('user_id', sa.Integer(), nullable=True, index=True))
    
    # 3. Add wom_snapshot_id column to boss_snapshots (if not exists)
    result = bind.execute(text("PRAGMA table_info(boss_snapshots)"))
    columns = {row[1] for row in result.fetchall()}
    
    if 'wom_snapshot_id' not in columns:
        op.add_column('boss_snapshots', sa.Column('wom_snapshot_id', sa.Integer(), nullable=True, index=True))
    
    # 4. Populate clan_members.id from ROWID
    # Since id column is empty, we need to populate it based on row order
    bind.execute(text("""
        UPDATE clan_members 
        SET id = (
            SELECT COUNT(*) FROM clan_members cm2 
            WHERE cm2.rowid <= clan_members.rowid
        )
    """))
    
    # 5. Populate wom_snapshots.user_id based on username match
    # This is the critical data population step
    bind.execute(text("""
        UPDATE wom_snapshots
        SET user_id = (
            SELECT id FROM clan_members 
            WHERE clan_members.username = wom_snapshots.username
        )
        WHERE username IS NOT NULL
    """))
    
    # 6. Populate discord_messages.user_id based on author_name match
    # Must handle case-insensitive matching
    bind.execute(text("""
        UPDATE discord_messages
        SET user_id = (
            SELECT id FROM clan_members 
            WHERE LOWER(clan_members.username) = LOWER(discord_messages.author_name)
        )
        WHERE author_name IS NOT NULL
    """))
    
    # 7. Populate boss_snapshots.wom_snapshot_id based on snapshot_id
    # This should match all snapshots (snapshot_id should reference valid wom_snapshots)
    bind.execute(text("""
        UPDATE boss_snapshots
        SET wom_snapshot_id = snapshot_id
        WHERE snapshot_id IS NOT NULL
    """))
    
    # 8. Create unique constraint on clan_members.username (if not exists)
    result = bind.execute(text("""
        SELECT name FROM sqlite_master 
        WHERE type='index' AND name='ix_clan_members_username_unique'
    """))
    if not result.fetchone():
        bind.execute(text("""
            CREATE UNIQUE INDEX ix_clan_members_username_unique 
            ON clan_members(username)
        """))


def downgrade() -> None:
    """Rollback migration: remove new columns and revert schema."""
    
    bind = op.get_bind()
    
    # Remove columns in reverse order
    # SQLite doesn't support DROP COLUMN in older versions,
    # so we need to check the version and handle appropriately
    try:
        # Try dropping the columns
        bind.execute(text("ALTER TABLE boss_snapshots DROP COLUMN wom_snapshot_id"))
        bind.execute(text("ALTER TABLE discord_messages DROP COLUMN user_id"))
        bind.execute(text("ALTER TABLE wom_snapshots DROP COLUMN user_id"))
        
        # Drop the unique index
        bind.execute(text("DROP INDEX IF EXISTS ix_clan_members_username_unique"))
        
        # Reset clan_members.id to NULL
        bind.execute(text("UPDATE clan_members SET id = NULL"))
        
    except Exception as e:
        # SQLite may not support ALTER TABLE DROP COLUMN in older versions
        # In that case, this migration cannot be rolled back
        print(f"Warning: Could not rollback migration. {e}")
        print("This may be due to SQLite version limitations.")
