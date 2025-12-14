
import sqlite3
import database
import os
from datetime import datetime, timedelta, timezone

def test_timestamps():
    print(f"DB Path: {database.DB_FILE}")
    conn = sqlite3.connect(database.DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # 1. Check raw values from DB
    c.execute("SELECT created_at FROM discord_messages ORDER BY created_at DESC LIMIT 5")
    rows = c.fetchall()
    
    print("\n--- Raw DB Timestamps (Top 5 Recent) ---")
    for r in rows:
        print(f"'{r['created_at']}'")
        
    # 2. Test Main.py Logic
    print("\n--- Testing Parsing Logic ---")
    cutoff_30d = datetime.now(timezone.utc) - timedelta(days=30)
    print(f"Cutoff 30d: {cutoff_30d}")
    
    valid_count = 0
    total_checked = 0
    
    c.execute("SELECT created_at FROM discord_messages")
    all_rows = c.fetchall()
    
    for r in all_rows:
        ts_str = r['created_at']
        total_checked += 1
        try:
            # Logic from main.py
            msg_dt = datetime.fromisoformat(ts_str.replace('Z', '+00:00')) if ts_str else datetime.min.replace(tzinfo=timezone.utc)
            
            if msg_dt >= cutoff_30d:
                valid_count += 1
                if valid_count <= 3:
                     print(f"PASS: {ts_str} -> {msg_dt}")
        except Exception as e:
            if total_checked <= 3:
                print(f"FAIL parsing '{ts_str}': {e}")
                
    print(f"\nTotal Rows: {total_checked}")
    print(f"Valid Rows (> 30d ago): {valid_count}")

if __name__ == "__main__":
    test_timestamps()
