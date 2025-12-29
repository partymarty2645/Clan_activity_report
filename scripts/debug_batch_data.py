import sqlite3

conn = sqlite3.connect('clan_data.db')
cursor = conn.cursor()

targets = ["lapislzuli", "dburke", "ciaomano", "hiku"]

print("--- user data check ---")
for t in targets:
    # 1. Check ID
    cursor.execute("SELECT id FROM clan_members WHERE username LIKE ?", (f"%{t}%",))
    res = cursor.fetchone()
    uid = res[0] if res else None
    
    # 2. Check Linked Msgs
    linked = 0
    if uid:
        cursor.execute("SELECT count(*) FROM discord_messages WHERE user_id=?", (uid,))
        linked = cursor.fetchone()[0]
        
    # 3. Check Unlinked Msgs
    cursor.execute("SELECT count(*) FROM discord_messages WHERE author_name LIKE ?", (f"%{t}%",))
    unlinked = cursor.fetchone()[0]
    
    print(f"User: {t} | ID: {uid} | Linked Msgs: {linked} | Unlinked Matches: {unlinked}")

conn.close()
