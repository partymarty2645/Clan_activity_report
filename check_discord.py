import sqlite3

conn = sqlite3.connect('clan_data.db')
conn.row_factory = sqlite3.Row

print("=== DISCORD_MESSAGES COLUMNS ===")
cursor = conn.execute("PRAGMA table_info(discord_messages);")
for col in cursor.fetchall():
    print(f"  {col['name']}: {col['type']}")

print("\n=== SAMPLE DISCORD_MESSAGES ===")
cursor = conn.execute("SELECT * FROM discord_messages LIMIT 1;")
cols = [description[0] for description in cursor.description]
row = cursor.fetchone()
if row:
    for col in cols:
        print(f"  {col}: {row[col]}")

print("\n=== DISCORD_MESSAGES STATS ===")
cursor = conn.execute("""
    SELECT 
        COUNT(*) as cnt,
        COUNT(DISTINCT author_id) as unique_authors,
        COUNT(DISTINCT author_name) as unique_author_names,
        MAX(timestamp) as latest,
        MIN(timestamp) as oldest
    FROM discord_messages;
""")
row = cursor.fetchone()
print(f"Total messages: {row['cnt']}")
print(f"Unique author_ids: {row['unique_authors']}")
print(f"Unique author_names: {row['unique_author_names']}")
print(f"Latest: {row['latest']}")
print(f"Oldest: {row['oldest']}")
