import sqlite3
import pandas as pd

conn = sqlite3.connect('clan_data.db')
cursor = conn.cursor()

# Check name match
cursor.execute("SELECT count(id) FROM discord_messages WHERE author_name LIKE '%masexd%'")
print(f"Messages strictly with author_name 'masexd': {cursor.fetchone()[0]}")

# Get ID
cursor.execute("SELECT id, username FROM clan_members WHERE username LIKE '%masexd%'")
user = cursor.fetchone()
if user:
    uid, uname = user
    print(f"Found User ID: {uid} (Username: {uname})")
    
    # Check Linked Messages
    cursor.execute("SELECT count(id) FROM discord_messages WHERE user_id = ?", (uid,))
    linked_count = cursor.fetchone()[0]
    print(f"Messages linked to User ID {uid}: {linked_count}")
    
    # Debug Linkage - why 0?
    if linked_count == 0:
        print("DEBUG: Checking unlinked messages that might be matches...")
        cursor.execute("SELECT author_name FROM discord_messages WHERE author_name LIKE ? LIMIT 5", (f"%{uname}%",))
        print("Potential Unlinked Matches:", cursor.fetchall())

else:
    print("User 'masexd' not found in clan_members table.")

conn.close()
