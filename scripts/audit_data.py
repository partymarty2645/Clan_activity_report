
import sqlite3
import pandas as pd
import logging
from rich.console import Console
from rich.table import Table

# Setup Logging
logging.basicConfig(level=logging.ERROR)
console = Console()

DB_PATH = "clan_data.db"

def get_db_connection():
    try:
        conn = sqlite3.connect(DB_PATH)
        return conn
    except sqlite3.Error as e:
        console.print(f"[red]Database connection error: {e}[/red]")
        return None

def audit_database():
    conn = get_db_connection()
    if not conn:
        return

    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall() if row[0] not in ['sqlite_sequence', 'alembic_version']]

    console.print(f"[bold blue]Starting Data Audit on {DB_PATH}...[/bold blue]\n")

    empty_columns_report = []

    for table_name in tables:
        console.print(f"Scanning table: [bold]{table_name}[/bold]...")
        
        # Read table into DataFrame (easier for column-wise analysis)
        try:
            df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
        except Exception as e:
            console.print(f"[red]Error reading {table_name}: {e}[/red]")
            continue
            
        if df.empty:
            console.print(f"[yellow]Table {table_name} is empty.[/yellow]")
            continue

        empty_cols = []
        for col in df.columns:
            # Check for "Empty": All values are 0, NULL (None), or Empty String
            # Convert to numeric if possible to catch string "0"
            try:
                numeric_series = pd.to_numeric(df[col], errors='coerce').fillna(0)
                is_all_zero = (numeric_series == 0).all()
            except:
                is_all_zero = False
                
            # Also check for pure nulls or empty strings if not numeric
            # We consider a column "unused" if it has NO meaningful data.
            # Meaningful = Non-Zero, Non-Null, Non-Empty String.
            
            # Count meaningful values
            # Filter out 0, 0.0, "0", None, NaN, ""
            meaningful_count = df[col].apply(lambda x: 
                x not in [0, 0.0, "0", None, "", "None", "nan"] 
                and pd.notna(x)
            ).sum()

            if meaningful_count == 0:
                empty_cols.append(col)

        if empty_cols:
            empty_columns_report.append({
                "table": table_name,
                "columns": empty_cols
            })

    conn.close()

    # Print Report
    console.print("\n[bold red]=== UNUSED / EMPTY COLUMNS FOUND ===[/bold red]")
    
    if not empty_columns_report:
        console.print("[green]No completely empty columns found![/green]")
    else:
        audit_table = Table(show_header=True, header_style="bold magenta")
        audit_table.add_column("Table Name", style="cyan")
        audit_table.add_column("Empty/Zero Columns", style="yellow")
        
        for item in empty_columns_report:
            audit_table.add_row(item['table'], ", ".join(item['columns']))
            
        console.print(audit_table)

if __name__ == "__main__":
    audit_database()
