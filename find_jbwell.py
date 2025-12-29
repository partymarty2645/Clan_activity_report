import sqlite3

conn = sqlite3.connect('clan_data.db')
cursor = conn.cursor()

# Search for JBwell
cursor.execute('SELECT username, role FROM clan_members WHERE username LIKE ? COLLATE NOCASE', ('%jb%',))
print("Players with 'JB' in name:")
results = cursor.fetchall()
for username, role in results:
    print(f"  {username} ({role})")

# Check all deputy_owner roles
print("\nAll deputy_owner roles:")
cursor.execute('SELECT username, role FROM clan_members WHERE role = ?', ('deputy_owner',))
for username, role in cursor.fetchall():
    print(f"  {username} ({role})")

conn.close()
