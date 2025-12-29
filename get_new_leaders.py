import sqlite3
conn = sqlite3.connect('clan_data.db')
cursor = conn.cursor()
cursor.execute('''
WITH recent AS (
    SELECT user_id, total_xp, total_boss_kills,
           ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY timestamp DESC) as rn
    FROM wom_snapshots
)
SELECT m.username, m.role, r.total_xp, r.total_boss_kills
FROM recent r
JOIN clan_members m ON m.id = r.user_id
WHERE m.username IN ('wonindstink', 'sir gowi')
AND r.rn = 1
ORDER BY r.total_xp DESC
''')
results = cursor.fetchall()
for username, role, xp, kills in results:
    print(f'{username} ({role}): {xp:,} XP, {kills:,} kills')
conn.close()
