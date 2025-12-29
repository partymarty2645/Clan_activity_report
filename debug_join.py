import sqlite3

conn = sqlite3.connect('clan_data.db')

cursor = conn.execute("SELECT COUNT(*) FROM boss_snapshots")
print('boss_snapshots rows:', cursor.fetchone()[0])

cursor = conn.execute("SELECT COUNT(*) FROM wom_snapshots")
print('wom_snapshots rows:', cursor.fetchone()[0])

cursor = conn.execute("SELECT COUNT(*) FROM boss_snapshots bs JOIN wom_snapshots ws ON bs.wom_snapshot_id = ws.id")
print('Join rows:', cursor.fetchone()[0])

# Check a few boss_snapshots
cursor = conn.execute("SELECT wom_snapshot_id, boss_name FROM boss_snapshots LIMIT 5")
print("\nSample boss_snapshots:")
for row in cursor.fetchall():
    print(f"  wom_snapshot_id={row[0]}, boss_name={row[1]}")

# Check if those wom_snapshot_ids exist
cursor = conn.execute("SELECT COUNT(*) FROM wom_snapshots WHERE id IN (SELECT wom_snapshot_id FROM boss_snapshots LIMIT 1)")
print(f"\nDo snapshot IDs exist? Count={cursor.fetchone()[0]}")
