import sqlite3
conn = sqlite3.connect('clan_data.db')
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
indexes = cursor.fetchall()
print("Existing indexes:")
for idx in indexes:
    print(f"  - {idx[0]}")
conn.close()
