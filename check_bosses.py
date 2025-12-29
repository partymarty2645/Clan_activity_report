import sqlite3

conn = sqlite3.connect('clan_data.db')
cursor = conn.execute("SELECT DISTINCT boss_name FROM boss_snapshots ORDER BY boss_name")
bosses = cursor.fetchall()

print("All unique bosses:")
for boss in bosses:
    print(f"  {boss[0]}")

print("\n\nRaid-related bosses (tomb, theatre, amascut, toa, tob):")
raid_bosses = [b[0] for b in bosses if any(x in str(b[0]).lower() for x in ['tomb', 'theatre', 'amascut', 'toa', 'tob'])]
for boss in raid_bosses:
    print(f"  {boss}")

if not raid_bosses:
    print("  (None found)")
