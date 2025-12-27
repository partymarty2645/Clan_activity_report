
import sqlite3
import pandas as pd
from rich.console import Console
from rich.table import Table
from datetime import datetime, timedelta

console = Console()
DB_PATH = "clan_data.db"

def check_db_health():
    try:
        conn = sqlite3.connect(DB_PATH)
    except Exception as e:
        console.print(f"[red]Failed to connect: {e}[/red]")
        return

    console.print(f"[bold blue]=== Deep Database Diagnostics ({DB_PATH}) ===[/bold blue]\n")

    # 1. ORPHAN CHECK
    console.print("[bold]1. Orphaned Data Check[/bold]")
    
    # Check 1a: Messages from unknown users
    # discord_messages has 'username' (text) and 'user_id' (text). 
    # clan_members has 'username' (text).
    # Ideally, distinct usernames in discord_messages should exist in clan_members if they are still in clan.
    
    # This might not be a 'hard' error if we keep history of left members, but worth noting.
    
    msg_users = pd.read_sql("SELECT DISTINCT author_name FROM discord_messages", conn)['author_name'].tolist()
    clan_users = pd.read_sql("SELECT DISTINCT username FROM clan_members", conn)['username'].tolist()
    
    orphans = [u for u in msg_users if u and u not in clan_users]
    if orphans:
        console.print(f"[yellow]Warning: {len(orphans)} users have messages but are not in 'clan_members' (Left clan or renamed?)[/yellow]")
        if len(orphans) < 5:
            console.print(f"   Examples: {', '.join(orphans[:5])}")
    else:
        console.print("[green]✔ All message authors exist in clan_members[/green]")


    # 2. STALENESS CHECK
    console.print("\n[bold]2. Data Staleness (WOM Snapshots)[/bold]")
    try:
        # Check max timestamp in wom_snapshots
        # Assuming there is a timestamp column? Let's check schema via query metadata or just try 'timestamp'
        # The audit showed wom_records is empty, so we look at wom_snapshots?
        # Let's inspect columns first to be safe
        snap_cols = pd.read_sql("PRAGMA table_info(wom_snapshots)", conn)['name'].tolist()
        
        date_col = next((c for c in snap_cols if 'time' in c or 'date' in c), None)
        
        if date_col:
            last_entry = pd.read_sql(f"SELECT MAX({date_col}) as last FROM wom_snapshots", conn)['last'].iloc[0]
            console.print(f"   Last Snapshot: [cyan]{last_entry}[/cyan]")
            
            # Check for totally stale users
            # "Users who haven't had a snapshot in > 7 days"
            latest_snaps = pd.read_sql(f"SELECT username, MAX({date_col}) as last_seen FROM wom_snapshots GROUP BY username", conn)
            latest_snaps['last_seen'] = pd.to_datetime(latest_snaps['last_seen'])
            
            now = datetime.now()
            stale_threshold = now - timedelta(days=7)
            stale_users = latest_snaps[latest_snaps['last_seen'] < stale_threshold]
            
            if not stale_users.empty:
                console.print(f"[red]!! {len(stale_users)} members have outdated WOM data (>7 days old) !![/red]")
                console.print(f"   Examples: {', '.join(stale_users['username'].head(3).tolist())}")
            else:
                 console.print("[green]✔ All members have recent WOM snapshots[/green]")
        else:
             console.print("[red]Could not identify timestamp column in wom_snapshots[/red]")

    except Exception as e:
        console.print(f"[red]Staleness check failed: {e}[/red]")

    # 3. LOGIC & CONSISTENCY
    console.print("\n[bold]3. Logic Anomaly Detection[/bold]")
    
    # 3a. Ghost Members (0 XP, 0 Boss, 0 Messages - Why are they here?)
    # Assuming 'clan_members' has aggregated stats columns like xp_total, boss_total?
    # If not, we might need to join tables.
    # Let's check clan_members columns.
    mem_cols = pd.read_sql("PRAGMA table_info(clan_members)", conn)['name'].tolist()
    
    # Heuristics based on likely column names
    xp_col = next((c for c in mem_cols if 'xp' in c and 'total' in c), 'total_xp')
    boss_col = next((c for c in mem_cols if 'boss' in c and 'total' in c), 'total_boss')
    
    # Join with message counts if not in member table
    # But wait, logic.js uses 'msgs_total'. 
    
    try:
        # Construct query based on available columns check
        # We'll just try to select * and analyze in pandas
        members = pd.read_sql("SELECT * FROM clan_members", conn)
        
        # Check if 0 XP users exist
        zero_xp = members[members[xp_col] == 0] if xp_col in members.columns else pd.DataFrame()
        
        if not zero_xp.empty:
             console.print(f"[yellow]Warning: {len(zero_xp)} members have 0 Total XP recorded.[/yellow]")
             
             # Check if these '0 XP' people have messages?
             if 'msgs_total' in members.columns:
                 active_ghosts = zero_xp[zero_xp['msgs_total'] > 10]
                 if not active_ghosts.empty:
                     console.print(f"[red]   Anomaly: {len(active_ghosts)} members have 0 XP but >10 Messages (Social only? Data error?)[/red]")
    except Exception as e:
        console.print(f"[red]Logic check failed: {e}[/red]")

    # 4. CRITICAL: Foreign Key Mismatch in Boss Snapshots
    console.print("\n[bold]4. Integrity Check: Boss Snapshots[/bold]")
    try:
        # Verify the finding from the previous audit: 'wom_snapshot_id'
        boss_snaps = pd.read_sql("SELECT count(*) as count, SUM(CASE WHEN wom_snapshot_id IS NULL OR wom_snapshot_id = 0 THEN 1 ELSE 0 END) as bad_links FROM boss_snapshots", conn)
        total = boss_snaps['count'].iloc[0]
        bad = boss_snaps['bad_links'].iloc[0]
        
        if bad > 0:
            console.print(f"[red]CRITICAL: {bad}/{total} boss_snapshots have invalid 'wom_snapshot_id' (Time correlation broken)[/red]")
        else:
             console.print("[green]✔ Boss Snapshots are correctly linked[/green]")
             
    except Exception as e:
        console.print(f"[red]Check failed: {e}[/red]")


    conn.close()

if __name__ == "__main__":
    check_db_health()
