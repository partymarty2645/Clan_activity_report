
import pandas as pd
import json
import os
from rich.console import Console
from rich.table import Table

console = Console()
JSON_PATH = "docs/clan_data.json"

def verify_json_integrity():
    if not os.path.exists(JSON_PATH):
        console.print(f"[bold red]JSON Export not found at {JSON_PATH}[/bold red]")
        return

    with open(JSON_PATH, 'r') as f:
        data = json.load(f)
        
    members = data.get('allMembers', [])
    df = pd.DataFrame(members)
    
    if df.empty:
        console.print("[bold red]No member data found in JSON![/bold red]")
        return

    # Force numeric types to avoid string comparison errors
    cols_to_numeric = ['xp_7d', 'total_xp', 'boss_7d', 'total_boss', 'msgs_7d', 'msgs_total', 'xp_30d', 'boss_30d', 'msgs_30d']
    for col in cols_to_numeric:
        df[col] = pd.to_numeric(df.get(col, 0), errors='coerce').fillna(0)

    console.print(f"\n[bold cyan]Auditing {len(df)} members from Dashboard Data[/bold cyan]")

    # 1. Impossible Zeros
    # (Checking for logic errors where 7d > Total)
    impossible = df[
        ((df['xp_7d'] > df['total_xp']) & (df['total_xp'] > 0)) |
        ((df['boss_7d'] > df['total_boss']) & (df['total_boss'] > 0)) |
        ((df['msgs_7d'] > df['msgs_total']) & (df['msgs_total'] > 0))
    ]
    
    if not impossible.empty:
        console.print("\n[bold yellow]WARNING: Data Constancy Issues (7d > Total):[/bold yellow]")
        for _, row in impossible.iterrows():
            reasons = []
            if row['xp_7d'] > row['total_xp']: reasons.append(f"XP({row['xp_7d']}>{row['total_xp']})")
            if row['boss_7d'] > row['total_boss']: reasons.append(f"Boss({row['boss_7d']}>{row['total_boss']})")
            if row['msgs_7d'] > row['msgs_total']: reasons.append(f"Msg({row['msgs_7d']}>{row['msgs_total']})")
            
            console.print(f"  - {row['username']}: {', '.join(reasons)}")
    else:
        console.print("\n[bold green]PASSED:[/bold green] Logic check (7d <= Total).")

    # 2. Analyze the "Zeros"
    # Are the 0s we see in dashboard valid?
    console.print("\n[bold blue]Zero-Value Analysis (Why are fields empty?):[/bold blue]")
    
    # 0 Messages Total
    zero_msgs = df[df['msgs_total'] == 0]
    # 0 XP Total (Should be very rare for active players)
    zero_xp = df[df['total_xp'] == 0]
    # 0 Boss Total
    zero_boss = df[df['total_boss'] == 0]
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Metric")
    table.add_column("Count")
    table.add_column("Details")
    
    table.add_row("0 Total Messages", str(len(zero_msgs)), f"{len(zero_msgs)/len(df)*100:.1f}% (Lurkers/Discord mismatch)")
    table.add_row("0 Total XP", str(len(zero_xp)), f"{len(zero_xp)/len(df)*100:.1f}% (New/Inactive/Tracking issue)")
    table.add_row("0 Total Boss Kills", str(len(zero_boss)), f"{len(zero_boss)/len(df)*100:.1f}% (Skillers/New)")
    
    console.print(table)
    
    # 3. Check specific "Suspicious" Zeros requested by user
    # "0 values that are highly unlikely" -> Active Message users with 0 XP?
    active_chat_zero_xp = df[(df['msgs_7d'] > 10) & (df['xp_7d'] == 0)]
    if not active_chat_zero_xp.empty:
        console.print("\n[bold yellow]Suspicious: Active in Chat (7d > 10) but 0 XP Gained:[/bold yellow]")
        for _, row in active_chat_zero_xp.iterrows():
            console.print(f"  - {row['username']} (Msgs: {row['msgs_7d']})")
            
    # Active XP users with 0 Chat?
    active_xp_zero_chat = df[(df['xp_7d'] > 500000) & (df['msgs_7d'] == 0)]
    if not active_xp_zero_chat.empty:
        console.print(f"\n[bold white]Context: {len(active_xp_zero_chat)} users gained >500k XP but sent 0 messages (Grinders).[/bold white]")

    # 4. Check for Heatmap Data presence
    if 'activity_heatmap' in data and len(data['activity_heatmap']) == 24:
         console.print("\n[bold green]PASSED:[/bold green] Heatmap data (24h) is present.")
    else:
         console.print("\n[bold red]FAILED:[/bold red] Heatmap data is missing or invalid.")


if __name__ == "__main__":
    verify_json_integrity()
