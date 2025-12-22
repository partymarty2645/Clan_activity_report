import sqlite3
import datetime
from datetime import timezone

DB_PATH = "clan_data.db"

def fix_timestamps():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("Fixing Timestamps in DB...")
    
    # 1. WOM Snapshots
    print("Checking wom_snapshots...")
    cursor.execute("SELECT id, timestamp FROM wom_snapshots")
    rows = cursor.fetchall()
    
    updates_wom = []
    for row in rows:
        ts_str = row['timestamp']
        if not ts_str: continue
        
        # Check if aware
        # Simple check: does it have "+" or "Z" near end? 
        # Or parse.
        try:
            # Replace space with T first if needed for parsing
            clean_ts = ts_str.replace(' ', 'T')
            
            # If naive, add +00:00
            # How to detect naive cleanly?
            # If it doesn't match standard offsets.
            # But converting to datetime object is surest.
            try:
                dt = datetime.datetime.fromisoformat(clean_ts)
            except ValueError:
                # Fallback for formats python doesn't like?
                continue
                
            if dt.tzinfo is None:
                # Naive -> Assume UTC -> Add string suffix
                # We want to store consistent string.
                # If original string was "2025-01-01 12:00:00.000", make it "2025-01-01T12:00:00.000+00:00"
                # Re-format
                dt = dt.replace(tzinfo=timezone.utc)
                new_ts = dt.isoformat() 
                # Note: isoformat() might use T. DB might have had spaces. T is better for ISO compliance.
                
                if new_ts != ts_str:
                     updates_wom.append((new_ts, row['id']))
            else:
                # Already aware. Just normalize to T separator if needed?
                # User complaint was mainly about the "same day" bug due to mismatched types.
                # Ensuring all are aware is key.
                # Let's verify formats conform to generic ISO (T separator)
                if ' ' in ts_str:
                     new_ts = ts_str.replace(' ', 'T')
                     updates_wom.append((new_ts, row['id']))

        except Exception as e:
            print(f"Skipping bad TS: {ts_str} ({e})")

    # Function to apply updates in batches
    def apply_batch(cursor, conn, table, col, updates, batch_size=5000):
        total = len(updates)
        if total == 0:
            print(f"{table} already clean.")
            return

        print(f"Updating {total} records in {table} in batches of {batch_size}...")
        for i in range(0, total, batch_size):
            batch = updates[i:i+batch_size]
            try:
                cursor.executemany(f"UPDATE {table} SET {col} = ? WHERE id = ?", batch)
                conn.commit()
                print(f"  Committed batch {i} - {min(i+batch_size, total)}")
            except Exception as e:
                print(f"  Error committing batch {i}: {e}")
                # Try to salvage? No, just continue or break
                
    if updates_wom:
        apply_batch(cursor, conn, "wom_snapshots", "timestamp", updates_wom)
    else:
        print("wom_snapshots already clean.")
        
    # 2. Discord Messages
    print("Checking discord_messages...")
    cursor.execute("SELECT id, created_at FROM discord_messages")
    rows = cursor.fetchall()
    
    updates_discord = []
    for row in rows:
        ts_str = row['created_at']
        if not ts_str: continue
        
        try:
             # Normalize parsing
             clean_ts = ts_str.replace(' ', 'T')
             try:
                 dt = datetime.datetime.fromisoformat(clean_ts)
             except ValueError:
                 continue
                 
             if dt.tzinfo is None:
                 dt = dt.replace(tzinfo=timezone.utc)
                 new_ts = dt.isoformat()
                 if new_ts != ts_str:
                     updates_discord.append((new_ts, row['id']))
             else:
                  # Ensure T separator
                  if ' ' in ts_str:
                      new_ts = ts_str.replace(' ', 'T')
                      updates_discord.append((new_ts, row['id']))
        except:
             pass
             
    if updates_discord:
        apply_batch(cursor, conn, "discord_messages", "created_at", updates_discord)
    else:
        print("discord_messages already clean.")

    conn.close()
    print("Done.")

if __name__ == "__main__":
    fix_timestamps()
