import sqlite3

conn = sqlite3.connect('clan_data.db')
conn.row_factory = sqlite3.Row

print("=== TABLE STRUCTURE ===")
cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
tables = cursor.fetchall()
print("Tables in database:")
for table in tables:
    print(f"  - {table['name']}")

print("\n=== WOM_SNAPSHOTS STATS ===")
cursor = conn.execute("""
    SELECT 
        COUNT(*) as cnt,
        COUNT(DISTINCT username) as unique_users,
        MAX(timestamp) as latest,
        MIN(timestamp) as oldest
    FROM wom_snapshots;
""")
row = cursor.fetchone()
print(f"Total snapshots: {row['cnt']}")
print(f"Unique users: {row['unique_users']}")
print(f"Latest: {row['latest']}")
print(f"Oldest: {row['oldest']}")

print("\n=== WOM_SNAPSHOTS COLUMNS ===")
cursor = conn.execute("PRAGMA table_info(wom_snapshots);")
for col in cursor.fetchall():
    print(f"  {col['name']}: {col['type']}")

print("\n=== SAMPLE WOM_SNAPSHOTS ===")
cursor = conn.execute("SELECT username, total_xp, timestamp FROM wom_snapshots ORDER BY username LIMIT 3;")
for row in cursor.fetchall():
    print(f"  {row['username']}: xp={row['total_xp']}, time={row['timestamp']}")

print("\n=== BOSS_SNAPSHOTS STATS ===")
cursor = conn.execute("""
    SELECT 
        COUNT(*) as cnt,
        COUNT(DISTINCT boss_name) as unique_bosses
    FROM boss_snapshots;
""")
row = cursor.fetchone()
print(f"Total boss records: {row['cnt']}")
print(f"Unique bosses: {row['unique_bosses']}")
