import sqlite3
import pandas as pd

try:
    conn = sqlite3.connect('clan_data.db')
    
    print("--- User: bagyy ---")
    
    # 1. Discord Messages
    print("\n[Discord Messages (Unique Authors matching 'bagyy')]")
    df_msgs = pd.read_sql_query("SELECT DISTINCT author_name FROM discord_messages WHERE author_name LIKE '%bagyy%'", conn)
    print(df_msgs.to_string())
    
    print("\n[Discord Messages (Count for 'bagyy')]")
    # Check exact match
    df_cnt = pd.read_sql_query("SELECT count(*) as count FROM discord_messages WHERE author_name = 'bagyy'", conn)
    print(df_cnt.to_string())
    
    # Check messages in last 7 days
    print("\n[Discord Messages (Last 7 Days)]")
    df_7d = pd.read_sql_query("SELECT count(*) as count FROM discord_messages WHERE author_name = 'bagyy' AND created_at >= date('now', '-7 days')", conn)
    print(df_7d.to_string())

    # 2. WOM Snapshots
    print("\n[WOM Snapshots (Timestamps for 'bagyy')]")
    df_snaps = pd.read_sql_query("SELECT timestamp, total_xp FROM wom_snapshots WHERE username = 'bagyy' ORDER BY timestamp DESC LIMIT 5", conn)
    print(df_snaps.to_string())

    # 3. Oldest Snapshot
    print("\n[Oldest Snapshot]")
    df_old = pd.read_sql_query("SELECT timestamp, total_xp FROM wom_snapshots WHERE username = 'bagyy' ORDER BY timestamp ASC LIMIT 1", conn)
    print(df_old.to_string())
    
    conn.close()
except Exception as e:
    print(e)
