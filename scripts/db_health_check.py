import sqlite3
import os
from rich.console import Console
from rich.table import Table

console = Console()
DB_FILE = "clan_data.db"

def check_health():
    if not os.path.exists(DB_FILE):
        console.print("[red]Database missing![/red]")
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    console.print("[bold cyan]=== THE ALCHEMIST'S HEALTH DIAGNOSTIC ===[/bold cyan]")

    # 1. FILE SIZE vs FRAGMENTATION
    file_size_mb = os.path.getsize(DB_FILE) / (1024 * 1024)
    
    # Pragma checks
    cursor.execute("PRAGMA page_count")
    page_count = cursor.fetchone()[0]
    cursor.execute("PRAGMA page_size")
    page_size = cursor.fetchone()[0]
    cursor.execute("PRAGMA freelist_count")
    freelist_count = cursor.fetchone()[0]
    
    frag_percent = (freelist_count / page_count) * 100 if page_count > 0 else 0
    
    console.print(f"[bold]Physical Specs:[/bold]")
    console.print(f" - Size: {file_size_mb:.2f} MB")
    console.print(f" - Pages: {page_count} (Size: {page_size})")
    console.print(f" - Free Pages: {freelist_count}")
    color = "red" if frag_percent > 10 else "green"
    console.print(f" - Fragmentation: [{color}]{frag_percent:.2f}%[/{color}]")

    # 2. ROW COUNTS & DENSITY
    tables = ['wom_snapshots', 'discord_messages', 'wom_records']
    rows = {}
    for t in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {t}")
            c = cursor.fetchone()[0]
            rows[t] = c
        except:
            rows[t] = 0
            
    console.print(f"\n[bold]Data Density:[/bold]")
    for t, c in rows.items():
        console.print(f" - {t}: {c:,} rows")

    # 3. INDEX CHECK (The "Speed" Check)
    console.print(f"\n[bold]Index Inventory:[/bold]")
    cursor.execute("PRAGMA index_list(wom_snapshots)")
    snaps_idx = cursor.fetchall()
    cursor.execute("PRAGMA index_list(discord_messages)")
    msg_idx = cursor.fetchall()
    
    found_idx = [i[1] for i in snaps_idx] + [i[1] for i in msg_idx]
    
    # Desired Indexes
    required = {
        'idx_wom_snapshot_date': 'Red', 
        'idx_discord_author_lower': 'Red',
        'idx_wom_snapshots_username_timestamp': 'Red'
    }
    
    for req in required:
        if req in found_idx:
            required[req] = 'Green'
            
    for req, status in required.items():
        color = 'green' if status == 'Green' else 'red'
        console.print(f" - {req}: [{color}]{status}[/{color}]")

    # 4. DUPLICATE/INTEGRITY (Sample)
    # Check for NULL usernames in latestsnapshots
    cursor.execute("SELECT COUNT(*) FROM wom_snapshots WHERE username IS NULL")
    null_users = cursor.fetchone()[0]
    
    console.print(f"\n[bold]Integrity Audit:[/bold]")
    console.print(f" - NULL usernames in snapshots: {'[red]' if null_users > 0 else '[green]'}{null_users}[/]")
    
    conn.close()

if __name__ == "__main__":
    check_health()
