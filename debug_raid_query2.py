import sqlite3

conn = sqlite3.connect('clan_data.db')
conn.row_factory = sqlite3.Row

# Try without GROUP BY first
query = """
    SELECT 
        bs.boss_name,
        COUNT(DISTINCT ws.username) as unique_players,
        SUM(bs.kills) as total_kills
    FROM boss_snapshots bs
    JOIN wom_snapshots ws ON bs.wom_snapshot_id = ws.id
    WHERE (bs.boss_name LIKE '%chambers%' OR bs.boss_name LIKE '%tombs%' OR bs.boss_name LIKE '%theatre_of_blood%')
    GROUP BY bs.boss_name
    ORDER BY total_kills DESC
    LIMIT 3
"""

print("Running debug query...")
cursor = conn.execute(query)
for row in cursor.fetchall():
    print(f"  {dict(row)}")

conn.close()
