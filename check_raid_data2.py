import sqlite3

conn = sqlite3.connect('clan_data.db')
conn.row_factory = sqlite3.Row

# Check boss_snapshots grouping by boss_name
query = """
    SELECT 
        boss_name,
        COUNT(*) as total_records,
        SUM(kills) as total_kills
    FROM boss_snapshots
    WHERE (boss_name LIKE '%chambers%' OR boss_name LIKE '%tombs%' OR boss_name LIKE '%theatre_of_blood%')
    GROUP BY boss_name
    ORDER BY total_kills DESC
"""

print("Raid data from boss_snapshots alone:")
cursor = conn.execute(query)
for row in cursor.fetchall():
    print(f"  {row['boss_name']}: {row['total_kills']:,} kills ({row['total_records']} records)")

conn.close()
