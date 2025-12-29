import sqlite3
from datetime import datetime, timezone

conn = sqlite3.connect('clan_data.db')
cursor = conn.cursor()

# Get latest snapshot timestamp
cursor.execute("SELECT MAX(timestamp) FROM wom_snapshots")
latest = cursor.fetchone()[0]
print(f"Latest snapshot in DB: {latest}")

# Get counts per player (top 5)
cursor.execute("""
SELECT username, COUNT(*) as snapshot_count 
FROM wom_snapshots 
GROUP BY username 
ORDER BY snapshot_count DESC 
LIMIT 10
""")
results = cursor.fetchall()
print("\nTop 10 players by snapshot count:")
for username, count in results:
    print(f"  {username}: {count} snapshots")

# Check if there are duplicate timestamps for same player
cursor.execute("""
SELECT username, timestamp, COUNT(*) 
FROM wom_snapshots 
GROUP BY username, timestamp 
HAVING COUNT(*) > 1 
LIMIT 10
""")
dups = cursor.fetchall()
if dups:
    print("\nDuplicates found (same player, same timestamp):")
    for username, ts, count in dups:
        print(f"  {username} @ {ts}: {count} records")
else:
    print("\nNo exact duplicates found (good!)")

# Average snapshots per player
cursor.execute("SELECT COUNT(*) / COUNT(DISTINCT username) FROM wom_snapshots")
avg = cursor.fetchone()[0]
print(f"\nAverage snapshots per player: {avg:.1f}")

conn.close()
