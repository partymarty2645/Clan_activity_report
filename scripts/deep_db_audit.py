
import sqlite3
import os
import sys
from rich.console import Console
from rich.table import Table

console = Console()
DB_PATH = "clan_data.db"

def run_audit():
    if not os.path.exists(DB_PATH):
        console.print("[red]Database not found![/red]")
        return

    console.print(f"[bold cyan]Deep Database Audit[/bold cyan] for: [yellow]{DB_PATH}[/yellow]")
    size_mb = os.path.getsize(DB_PATH) / (1024 * 1024)
    console.print(f"Total File Size: [bold]{size_mb:.2f} MB[/bold]\n")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Table Sizes
    console.print("[bold]1. Table Row Counts[/bold]")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall() if row[0] != 'sqlite_sequence']
    
    t_table = Table(title="Row Counts")
    t_table.add_column("Table", style="cyan")
    t_table.add_column("Rows", justify="right")
    
    for table in tables:
        count = cursor.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
        t_table.add_row(table, f"{count:,}")
    console.print(t_table)
    console.print("")

    # 2. Zero-Entry Analysis (wom_snapshots)
    console.print("[bold]2. Zero-Data Entries (wom_snapshots)[/bold]")
    users = cursor.execute("SELECT count(DISTINCT username) FROM wom_snapshots").fetchone()[0]
    
    # Snapshots with 0 XP
    zero_xp = cursor.execute("SELECT count(*) FROM wom_snapshots WHERE total_xp = 0").fetchone()[0]
    
    # Snapshots with 0 Boss Kills
    zero_boss = cursor.execute("SELECT count(*) FROM wom_snapshots WHERE total_boss_kills = 0").fetchone()[0]
    
    # Snapshots with 0 XP AND 0 Boss Kills (Truly empty?)
    zero_both = cursor.execute("SELECT count(*) FROM wom_snapshots WHERE total_xp = 0 AND total_boss_kills = 0").fetchone()[0]

    console.print(f"Total Unique Users in History: {users}")
    console.print(f"Snapshots with 0 XP: [red]{zero_xp:,}[/red]")
    console.print(f"Snapshots with 0 Boss Kills: [red]{zero_boss:,}[/red]")
    console.print(f"Snapshots with 0 XP & 0 Kills: [bold red]{zero_both:,}[/bold red]")
    
    if zero_both > 0:
        console.print("  [yellow]Sample Empty Users:[/yellow]")
        cursor.execute("SELECT username, count(*) as c FROM wom_snapshots WHERE total_xp = 0 AND total_boss_kills = 0 GROUP BY username ORDER BY c DESC LIMIT 5")
        for row in cursor.fetchall():
            console.print(f"    - {row[0]}: {row[1]} empty snapshots")
    console.print("")

    # 3. Orphan Analysis
    console.print("[bold]3. Orphaned Data Check[/bold]")
    
    # Boss Snapshots without Parent
    orphaned_boss_snaps = 0
    try:
        orphaned_boss_snaps = cursor.execute("""
            SELECT count(*) FROM boss_snapshots 
            WHERE wom_snapshot_id NOT IN (SELECT id FROM wom_snapshots)
        """).fetchone()[0]
    except Exception as e:
        console.print(f"[red]Error checking boss orphans: {e}[/red]")

    console.print(f"Orphaned Boss Records: {orphaned_boss_snaps}")
    
    # 4. Large Objects (Raw JSON)
    console.print("\n[bold]4. Storage Heavyweights[/bold]")
    try:
        # Estimate average size of raw_data
        avg_json_size = cursor.execute("SELECT avg(length(raw_data)) FROM wom_snapshots").fetchone()[0] 
        total_rows = cursor.execute("SELECT count(*) FROM wom_snapshots").fetchone()[0]
        
        if avg_json_size:
            est_json_mb = (avg_json_size * total_rows) / (1024*1024)
            console.print(f"Avg 'raw_data' JSON size: {avg_json_size:.0f} bytes")
            console.print(f"Estimated Total JSON Storage: [bold red]{est_json_mb:.2f} MB[/bold red]")
    except Exception as e:
        console.print(f"[dim]Could not estimate JSON size: {e}[/dim]")

    conn.close()

if __name__ == "__main__":
    run_audit()
