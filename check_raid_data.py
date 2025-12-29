import sqlite3

conn = sqlite3.connect('clan_data.db')

# Check ALL raid data (no time filter)
print("All raid data in database:")
cursor = conn.execute("""
    SELECT bs.boss_name, COUNT(*) as count
    FROM boss_snapshots bs
    WHERE (bs.boss_name LIKE '%chambers%' OR bs.boss_name LIKE '%tombs%' OR bs.boss_name LIKE '%theatre_of_blood%')
    GROUP BY bs.boss_name
""")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]}")

# Check raid data from last 7 days
print("\nRaid data from last 7 days:")
cursor = conn.execute("""
    SELECT bs.boss_name, COUNT(*) as count
    FROM boss_snapshots bs
    JOIN wom_snapshots ws ON bs.wom_snapshot_id = ws.id
    WHERE (bs.boss_name LIKE '%chambers%' OR bs.boss_name LIKE '%tombs%' OR bs.boss_name LIKE '%theatre_of_blood%')
    AND ws.timestamp >= datetime('now', '-7 days')
    GROUP BY bs.boss_name
""")
rows = cursor.fetchall()
if rows:
    for row in rows:
        print(f"  {row[0]}: {row[1]}")
else:
    print("  (None found)")

# Check latest snapshot
print("\nLatest snapshot dates:")
cursor = conn.execute("SELECT MIN(timestamp), MAX(timestamp) FROM wom_snapshots")
print(f"  {cursor.fetchone()}")
