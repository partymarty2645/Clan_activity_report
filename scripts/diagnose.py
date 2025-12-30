
import sys
import os
import argparse
import sqlite3
import pandas as pd
import json
from rich.console import Console
from rich.table import Table

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import Config

console = Console()

DB_PATH = Config.DB_FILE
JSON_PATH = "docs/clan_data.json"

def check_schema():
    console.print(f"\n[bold icon] Checking Schema for {DB_PATH}...[/bold icon]")
    if not os.path.exists(DB_PATH):
        console.print(f"[bold red]Database not found at {DB_PATH}[/bold red]")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = cursor.fetchall()
    
    for table in tables:
        table_name = table[0]
        console.print(f"\n[bold cyan]{table_name}[/bold cyan]:")
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        
        # Get row count
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        
        # Simple column listing
        col_str = ", ".join([f"{c[1]}({c[2]})" for c in columns])
        console.print(f"  Columns: {col_str}")
        console.print(f"  Rows: [bold white]{count}[/bold white]")
        
    conn.close()

def check_bosses():
    console.print(f"\n[bold icon] Checking Boss Data...[/bold icon]")
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.execute("SELECT DISTINCT boss_name FROM boss_snapshots ORDER BY boss_name")
        bosses = [b[0] for b in cursor.fetchall()]
        
        console.print(f"Total Unique Bosses: {len(bosses)}")
        
        # Check specific raid bosses
        raid_keywords = ['tomb', 'theatre', 'amascut', 'toa', 'tob', 'chambers', 'cox']
        raid_bosses = [b for b in bosses if any(k in str(b).lower() for k in raid_keywords)]
        
        if raid_bosses:
            console.print("\n[bold green]Raid Bosses Found:[/bold green]")
            for rb in raid_bosses:
                console.print(f"  - {rb}")
        else:
            console.print("\n[bold red]WARNING: No Raid Bosses found![/bold red]")
            
    except Exception as e:
        console.print(f"[bold red]Error checking bosses: {e}[/bold red]")
    finally:
        conn.close()

def verify_integrity():
    console.print(f"\n[bold icon] Verifying Data Integrity (JSON Export)...[/bold icon]")
    
    if not os.path.exists(JSON_PATH):
        console.print(f"[bold red]JSON Export not found at {JSON_PATH}[/bold red]")
        return

    try:
        with open(JSON_PATH, 'r') as f:
            data = json.load(f)
            
        members = data.get('allMembers', [])
        df = pd.DataFrame(members)
        
        if df.empty:
            console.print("[bold red]No member data found in JSON![/bold red]")
            return

        # Force numeric
        cols = ['xp_7d', 'total_xp', 'boss_7d', 'total_boss', 'msgs_7d', 'msgs_total']
        for col in cols:
            df[col] = pd.to_numeric(df.get(col, 0), errors='coerce').fillna(0)

        # 1. Impossible Zeros
        impossible = df[
            ((df['xp_7d'] > df['total_xp']) & (df['total_xp'] > 0)) |
            ((df['boss_7d'] > df['total_boss']) & (df['total_boss'] > 0)) |
            ((df['msgs_7d'] > df['msgs_total']) & (df['msgs_total'] > 0))
        ]
        
        if not impossible.empty:
            console.print("[bold yellow]WARNING: Logic Issues (7d > Total)[/bold yellow]")
            console.print(impossible[['username', 'xp_7d', 'total_xp', 'boss_7d', 'total_boss']].head().to_string())
        else:
            console.print("[green]✓ Logic Check Passed (7d <= Total)[/green]")
            
        # 2. Zero Analysis
        zeros = {
            'Msgs': len(df[df['msgs_total'] == 0]),
            'XP': len(df[df['total_xp'] == 0]),
            'Boss': len(df[df['total_boss'] == 0])
        }
        console.print("\n[bold]Zero Value Counts:[/bold]")
        for k, v in zeros.items():
            console.print(f"  - 0 Total {k}: {v} ({v/len(df)*100:.1f}%)")

        # 3. Heatmap
        if 'activity_heatmap' in data and len(data['activity_heatmap']) == 24:
             console.print("[green]✓ Heatmap Data Present[/green]")
        else:
             console.print("[red]✗ Heatmap Data Missing/Invalid[/red]")
             
    except Exception as e:
        console.print(f"[bold red]Integrity check failed: {e}[/bold red]")

def main():
    parser = argparse.ArgumentParser(description="ClanStats Diagnostic Tool")
    parser.add_argument("--schema", action="store_true", help="Show database schema and row counts")
    parser.add_argument("--bosses", action="store_true", help="List unique bosses and check for raids")
    parser.add_argument("--integrity", action="store_true", help="Verify JSON export integrity")
    parser.add_argument("--full", action="store_true", help="Run all checks")
    
    args = parser.parse_args()
    
    if args.full:
        args.schema = True
        args.bosses = True
        args.integrity = True
        
    if args.schema:
        check_schema()
        
    if args.bosses:
        check_bosses()
        
    if args.integrity:
        verify_integrity()
        
    if not any([args.schema, args.bosses, args.integrity, args.full]):
        parser.print_help()

if __name__ == "__main__":
    main()
