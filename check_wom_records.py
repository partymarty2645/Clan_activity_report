import sqlite3

conn = sqlite3.connect('clan_data.db')
cursor = conn.execute("PRAGMA table_info(wom_records);")
print("wom_records table schema:")
for row in cursor.fetchall():
    print(row)

print("\n\nSample data from wom_records:")
cursor = conn.execute("SELECT * FROM wom_records LIMIT 1;")
cols = [description[0] for description in cursor.description]
print("Columns:", cols)
row = cursor.fetchone()
if row:
    for i, col in enumerate(cols):
        print(f"  {col}: {row[i]}")
