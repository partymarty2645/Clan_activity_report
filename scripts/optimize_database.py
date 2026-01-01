"""
DATABASE OPTIMIZER (The Alchemist's Transmutation)
==================================================
This script performs a surgical operation on the database to:
1. Remove redundant indexes that slow down writes.
2. Create 'Functional Indexes' to speed up harvest.py and report.py.
3. Vacuum the database to reduce file size.

Author: Agent 6
"""
import sqlite3
import time
import os
import sys
from rich.console import Console
from core.config import Config

console = Console()

def optimize():
    if not os.path.exists(Config.DB_FILE):
        console.print("[red]Database not found![/red]")
        return

    # Measure before
    size_before = os.path.getsize(Config.DB_FILE) / (1024*1024)
    console.print(f"[bold cyan]Starting Optimization... (Current Size: {size_before:.2f} MB)[/bold cyan]")

    conn = sqlite3.connect(Config.DB_FILE)
    # Set a 60-second timeout to wait for locks to clear (harvesting etc)
    conn.execute("PRAGMA busy_timeout = 60000")
    
    # Enable WAL mode for better concurrency (Writer doesn't block Readers)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        console.print("  + Enabled WAL (Write-Ahead Logging) mode.")
    except Exception as e:
        console.print(f"  ! Failed to enable WAL mode: {e}")
            
    cursor = conn.cursor()

    # 0. INTEGRITY CHECK (Fail fast if corrupt)
    console.print("[cyan]Phase 0: Verifying Database Integrity...[/cyan]")
    try:
        integrity = cursor.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            console.print(f"[bold red]CRITICAL: Database integrity check failed: {integrity}[/bold red]")
            conn.close()
            sys.exit(1)
        console.print("  + Integrity check passed.")
    except Exception as e:
        console.print(f"[bold red]CRITICAL: Failed to run integrity check: {e}[/bold red]")
        sys.exit(1)

    # 1. DROP DUPLICATES & OBSOLETE
    # We prioritize the named 'idx_' versions usually, but we'll stick to a clean naming convention.
    droplist = [
        "ix_wom_snapshots_timestamp",        # Duplicate of idx_wom_snapshots_timestamp
        "ix_wom_snapshots_username",         # Covered by compound or other index
        "idx_discord_messages_created",      # Duplicate of idx_discord_messages_created_at
        "ix_discord_messages_created_at",    # Triplicate?
        "idx_wom_snapshot_date",             # Drop if exists to recreate
    ]

    console.print("[yellow]Phase 1: Pruning Redundant Indexes...[/yellow]")
    count_dropped = 0
    for idx in droplist:
        try:
            # Check existence first to avoid noisy logs
            exists = cursor.execute("SELECT 1 FROM sqlite_master WHERE type='index' AND name=?", (idx,)).fetchone()
            if exists:
                cursor.execute(f"DROP INDEX {idx}")
                console.print(f"  - Dropped {idx}")
                count_dropped += 1
        except Exception as e:
            console.print(f"  - Error dropping {idx}: {e}")
            
    if count_dropped == 0:
        console.print("  - No redundant indexes found.")

    # 2. CREATE OPTIMIZED INDEXES (The Top 3 + Cleanups)
    
    # Index 1: Standard Timestamp Index for Harvest (Daily Lock)
    # The new harvester checks `timestamp >= ?`, so we need a direct index on timestamp, not date()
    console.print("[green]Phase 2: Forging New Indexes...[/green]")
    try:
        # Check if already exists to silence log
        exists = cursor.execute("SELECT 1 FROM sqlite_master WHERE type='index' AND name='idx_wom_snapshots_timestamp'").fetchone()
        if not exists:
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_wom_snapshots_timestamp ON wom_snapshots(timestamp)")
            console.print("  + Created index: idx_wom_snapshots_timestamp (Speeds up Harvest Freshness Check)")
    except Exception as e:
        console.print(f"  ! Failed idx_wom_snapshots_timestamp: {e}")

    # Index 2: Functional Index for Report (Author Grouping)
    # Speeds up message counting by author case-insensitively
    try:
        exists = cursor.execute("SELECT 1 FROM sqlite_master WHERE type='index' AND name='idx_discord_author_lower'").fetchone()
        if not exists:
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_discord_author_lower ON discord_messages(lower(author_name))")
            console.print("  + Created functional index: idx_discord_author_lower (Speeds up Report Message Counts)")
    except Exception as e:
        console.print(f"  ! Failed idx_discord_author_lower: {e}")

    # Index 3: Compound Indexes for AI Analyst Queries
    # These speed up the most expensive queries in ai_analyst.py
    try:
        # Verify core single-column indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_discord_messages_created_at ON discord_messages(created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_wom_snapshots_username_timestamp ON wom_snapshots(username, timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_username ON wom_snapshots(username)")
        
        # Compound index for boss diversity queries
        # Query: SELECT boss_name, COUNT(*) FROM boss_snapshots WHERE snapshot_id IN (...) GROUP BY boss_name
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_boss_snapshots_snapshot_boss ON boss_snapshots(snapshot_id, boss_name)")
        
        # Compound index for Discord message reports
        # Query: SELECT author_name, COUNT(*) FROM discord_messages WHERE created_at > X GROUP BY author_name
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_discord_created_author ON discord_messages(created_at, author_name)")
        
        # Index for WOM record filtering by thresholds
        # Query: SELECT * FROM wom_records WHERE xp_custom > X ORDER BY xp_custom DESC
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_wom_records_xp_custom ON wom_records(xp_custom DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_wom_records_msg_custom ON wom_records(msg_custom DESC)")
        
        # Compound index for clan member lookups with join_date
        # Query: SELECT * FROM clan_members WHERE joined_at > X
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_clan_members_joined_at ON clan_members(joined_at DESC)")
        
        # Compound index for player aliases by source and current status
        # Query: SELECT * FROM player_name_aliases WHERE source = X AND is_current = TRUE
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_aliases_source_current ON player_name_aliases(source, is_current)")
        
        console.print("  + Created 7 new compound indexes for query optimization")
    except Exception as e:
        console.print(f"  ! Error creating compound indexes: {e}")

    conn.commit()

    # 3. VACUUM & ANALYZE
    console.print("[magenta]Phase 3: Vacuuming & Analyzing (Low Memory Mode)...[/magenta]")
    start = time.time()
    try:
        # SQLite VACUUM requires no transaction block usually, but python handles it.
        conn.isolation_level = None # Autocommit mode for VACUUM
        
        # Low Memory Optimization Settings
        cursor.execute("PRAGMA cache_size = -2048") # Limit to ~2MB
        cursor.execute("PRAGMA temp_store = FILE")  # Use disk instead of RAM for temp storage
        cursor.execute("PRAGMA synchronous = NORMAL") # Good balance for maintenance

        try:
            # Re-enabling VACUUM but handling potentially locked DB
            console.print("  - Running VACUUM (Rebuilds DB file to reclaim space)...")
            cursor.execute("VACUUM")
            console.print(f"  - VACUUM finished in {time.time() - start:.2f}s")
            
            console.print("  - Running PRAGMA optimize (Updates query planner statistics)...")
            cursor.execute("PRAGMA optimize")
            
            console.print("  - Running WAL Checkpoint (Cleaning up temporary .wal file)...")
            # TRUNCATE resets the WAL file length to zero, freeing disk space immediately
            cursor.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            
            console.print("  - Optimize finished.")
            
        except sqlite3.OperationalError as e:
             console.print(f"[yellow]WARNING: VACUUM failed ({e}). Database might be locked. Skipping compaction.[/yellow]")
        except Exception as e:
             console.print(f"[yellow]WARNING: VACUUM failed with unexpected error ({e}). Skipping.[/yellow]")

    except Exception as e:
        console.print(f"[red]Error during optimization phase 3: {e}[/red]")

    conn.close()

    # Measure after
    size_after = os.path.getsize(Config.DB_FILE) / (1024*1024)
    saved = size_before - size_after
    console.print(f"[bold green]Optimization Complete![/bold green]")
    if saved > 0.01:
        console.print(f"New Size: {size_after:.2f} MB (Saved {saved:.2f} MB)")
    else:
        console.print(f"New Size: {size_after:.2f} MB (Database was already optimized)")

if __name__ == "__main__":
    optimize()
