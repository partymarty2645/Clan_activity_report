"""
DATABASE OPTIMIZER (The Alchemist's Transmutation)
==================================================
This script performs a surgical operation on 'clan_data.db' to:
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

console = Console()
DB_PATH = "clan_data.db"

def optimize():
    if not os.path.exists(DB_PATH):
        console.print("[red]Database not found![/red]")
        return

    # Measure before
    size_before = os.path.getsize(DB_PATH) / (1024*1024)
    console.print(f"[bold cyan]Starting Optimization... (Current Size: {size_before:.2f} MB)[/bold cyan]")

    conn = sqlite3.connect(DB_PATH)
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
        "idx_discord_author_lower"           # Drop if exists to recreate
    ]

    console.print("[yellow]Phase 1: Pruning Redundant Indexes...[/yellow]")
    for idx in droplist:
        try:
            cursor.execute(f"DROP INDEX IF EXISTS {idx}")
            console.print(f"  - Dropped {idx}")
        except Exception as e:
            console.print(f"  - Error dropping {idx}: {e}")

    # 2. CREATE OPTIMIZED INDEXES (The Top 3 + Cleanups)
    
    # Index 1: Functional Index for Harvest (Daily Lock)
    # Replaces the need for full table scan on `func.date(timestamp)`
    console.print("[green]Phase 2: Forging New Indexes...[/green]")
    try:
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_wom_snapshot_date ON wom_snapshots(date(timestamp))")
        console.print("  + Created functional index: idx_wom_snapshot_date (Speeds up Harvest Daily Check)")
    except Exception as e:
        console.print(f"  ! Failed idx_wom_snapshot_date: {e}")

    # Index 2: Functional Index for Report (Author Grouping)
    # Speeds up message counting by author case-insensitively
    try:
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_discord_author_lower ON discord_messages(lower(author_name))")
        console.print("  + Created functional index: idx_discord_author_lower (Speeds up Report Message Counts)")
    except Exception as e:
        console.print(f"  ! Failed idx_discord_author_lower: {e}")

    # Index 3: Covering Index for Discord Reports (Date + Author)
    # Optimized for "Where Date between X and Y"
    try:
        # We ensure we have the clean standard indexes too
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_discord_messages_created_at ON discord_messages(created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_wom_snapshots_username_timestamp ON wom_snapshots(username, timestamp)")
        console.print("  + Verified core covering indexes.")
    except Exception as e:
        console.print(f"  ! Error verifying core indexes: {e}")

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
        cursor.execute("PRAGMA synchronous = FULL") # Ensure safety

        cursor.execute("VACUUM")
        cursor.execute("ANALYZE")
        console.print(f"  - Vacuum Complete in {time.time() - start:.2f}s")
    except Exception as e:
        if "disk I/O" in str(e):
            console.print(f"[yellow]WARNING: VACUUM failed (disk I/O error). Skipping compaction to allow pipeline to continue.[/yellow]")
        else:
            console.print(f"  ! Vacuum failed: {e}")
            conn.close()
            sys.exit(1)

    conn.close()

    # Measure after
    size_after = os.path.getsize(DB_PATH) / (1024*1024)
    saved = size_before - size_after
    console.print(f"[bold green]Optimization Complete![/bold green]")
    console.print(f"New Size: {size_after:.2f} MB (Saved {saved:.2f} MB)")

if __name__ == "__main__":
    optimize()
