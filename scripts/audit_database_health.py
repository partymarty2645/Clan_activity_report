import sqlite3
import pandas as pd
from rich.console import Console
from rich.table import Table

console = Console()

DB_PATH = 'clan_data.db'

def get_tables(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    return [r[0] for r in cursor.fetchall()]

def check_pk(conn, table_name):
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    # cid, name, type, notnull, dflt_value, pk
    pks = [c[1] for c in columns if c[5] > 0]
    return pks

def check_indexes(conn, table_name):
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA index_list({table_name})")
    indexes = cursor.fetchall()
    return len(indexes)

def check_nulls(conn, table_name):
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    
    null_counts = {}
    for col in columns:
        col_name = col[1]
        is_not_null = col[3]
        if not is_not_null: # If nullable, check if it has nulls
            cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE {col_name} IS NULL")
            count = cursor.fetchone()[0]
            if count > 0:
                null_counts[col_name] = count
    return null_counts

def main():
    try:
        conn = sqlite3.connect(DB_PATH)
        tables = get_tables(conn)
        
        console.print(f"[bold green]Found {len(tables)} tables[/bold green]")
        
        table_overview = Table(title="Table Overview")
        table_overview.add_column("Table Name", style="cyan")
        table_overview.add_column("PKs", style="magenta")
        table_overview.add_column("Indexes", style="green")
        table_overview.add_column("Null Issues", style="red")
        
        for table in tables:
            if table.startswith('sqlite_'): continue
            
            pks = check_pk(conn, table)
            indexes = check_indexes(conn, table)
            nulls = check_nulls(conn, table)
            
            null_str = ", ".join([f"{k}: {v}" for k, v in nulls.items()]) if nulls else "None"
            
            table_overview.add_row(
                table,
                ", ".join(pks) if pks else "[bold red]MISSING[/bold red]",
                str(indexes),
                null_str
            )
            
        console.print(table_overview)
        
        # Specific Checks
        console.print("\n[bold]Specific Bad Habit Checks:[/bold]")
        
        # Check 1: Foreign Keys
        fk_on = conn.execute("PRAGMA foreign_keys").fetchone()[0]
        console.print(f"Foreign Keys Enabled: {'[green]YES[/green]' if fk_on else '[red]NO[/red]'}")
        
        conn.close()
        
    except Exception as e:
        console.print(f"[bold red]Error checking database: {e}[/bold red]")

if __name__ == "__main__":
    main()
