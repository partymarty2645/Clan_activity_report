"""add indexes for performance

Revision ID: add_indexes_001
Revises: b1dda54d7b09
Create Date: 2025-12-17 08:30:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_indexes_001'
down_revision = 'b1dda54d7b09'
branch_labels = None
depends_on = None


def upgrade():
    # Add indexes for commonly queried columns
    # These will dramatically improve query performance
    
    # WOM Snapshots - username and timestamp are frequently used together
    op.create_index('idx_wom_snapshots_username_timestamp', 'wom_snapshots', ['username', 'timestamp'])
    op.create_index('idx_wom_snapshots_timestamp', 'wom_snapshots', ['timestamp'])
    
    # Discord Messages - created_at for time-based queries
    op.create_index('idx_discord_messages_created_at', 'discord_messages', ['created_at'])
    op.create_index('idx_discord_messages_author_created', 'discord_messages', ['author_name', 'created_at'])
    
    # WOM Records - for quick lookups
    op.create_index('idx_wom_records_username_fetch', 'wom_records', ['username', 'fetch_date'])


def downgrade():
    # Remove indexes if rolling back
    op.drop_index('idx_wom_records_username_fetch', table_name='wom_records')
    op.drop_index('idx_discord_messages_author_created', table_name='discord_messages')
    op.drop_index('idx_discord_messages_created_at', table_name='discord_messages')
    op.drop_index('idx_wom_snapshots_timestamp', table_name='wom_snapshots')
    op.drop_index('idx_wom_snapshots_username_timestamp', table_name='wom_snapshots')
