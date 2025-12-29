import sqlite3

DB_PATH = "clan_data.db"

targets = ["kushtikev420", "xterminater", "p2k", "reagan921"]

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("--- DB Verification ---")
for t in targets:
    # Get ID
    cursor.execute("SELECT id, username FROM clan_members WHERE username = ?", (t,))
    rows = cursor.fetchall()
    if not rows:
        print(f"❌ '{t}' NOT FOUND in clan_members!")
        continue
    
    print(f"Found {len(rows)} matching members for '{t}': {rows}")
    
    for r in rows:
        mid = r[0]
        # Count Messages
        cursor.execute(f"SELECT COUNT(*) FROM discord_messages WHERE user_id = {mid}")
        count = cursor.fetchone()[0]
        print(f"✅ ID {mid} ('{r[1]}'): {count} Messages")

conn.close()
