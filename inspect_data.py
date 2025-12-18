import json
import sqlite3

# Inspect JSON
print("--- JSON KEYS ---")
try:
    with open('e:/Clan_activity_report/clan_data.json', 'r') as f:
        data = json.load(f)
        print(data.keys())
        if 'members' in data:
            print(f"Found 'members' key with {len(data['members'])} items.")
            # Print first member keys
            first_member = next(iter(data['members'].values())) if isinstance(data['members'], dict) else data['members'][0]
            print("Member Keys:", first_member.keys())
        else:
            print("'members' key NOT found.")
except Exception as e:
    print(f"JSON Error: {e}")

# Inspect DB Tables
print("\n--- DB TABLES ---")
try:
    conn = sqlite3.connect('e:/Clan_activity_report/clan_data.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("Tables:", [t[0] for t in tables])
    
    # Check simple_activity columns if it exists
    if ('simple_activity',) in tables:
        cursor.execute("PRAGMA table_info(simple_activity)")
        print("simple_activity columns:", cursor.fetchall())

    conn.close()
except Exception as e:
    print(f"DB Error: {e}")
