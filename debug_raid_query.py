import sqlite3

conn = sqlite3.connect('clan_data.db')
conn.row_factory = sqlite3.Row

# Debug the exact query
query = """
    SELECT 
        CASE 
            WHEN bs.boss_name LIKE '%chambers%' THEN 'CoX'
            WHEN bs.boss_name LIKE '%tombs%' THEN 'ToA'
            WHEN bs.boss_name LIKE '%theatre_of_blood%' THEN 'ToB'
        END as raid_type,
        COUNT(DISTINCT ws.username) as unique_players,
        SUM(bs.kills) as total_kills
    FROM boss_snapshots bs
    JOIN wom_snapshots ws ON bs.wom_snapshot_id = ws.id
    WHERE (bs.boss_name LIKE '%chambers%' OR bs.boss_name LIKE '%tombs%' OR bs.boss_name LIKE '%theatre_of_blood%')
    GROUP BY raid_type
    ORDER BY total_kills DESC
    LIMIT 1
"""

print("Running query...")
try:
    cursor = conn.execute(query)
    result = cursor.fetchone()
    if result:
        print(f"Result: {dict(result)}")
    else:
        print("No result returned")
except Exception as e:
    print(f"Error: {e}")

conn.close()
