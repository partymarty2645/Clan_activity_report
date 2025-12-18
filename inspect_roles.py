import sqlite3
import json

conn = sqlite3.connect('e:/Clan_activity_report/clan_data.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("--- Checking wom_snapshots for Roles ---")
cursor.execute("SELECT username, raw_data FROM wom_snapshots ORDER BY timestamp DESC LIMIT 5")
rows = cursor.fetchall()

for row in rows:
    if row['raw_data']:
        try:
            data = json.loads(row['raw_data'])
            # Check for role field in common places
            role = data.get('role') # sometimes top level
            if not role and 'data' in data:
                role = data['data'].get('role')
            if not role and 'player' in data: # sometimes in player
                 role = data['player'].get('role')
            
            print(f"User: {row['username']}, Role: {role}")
            # print(data.keys()) 
        except Exception as e:
            print(f"Error parsing json for {row['username']}: {e}")
    else:
        print(f"User: {row['username']} - No raw data")

conn.close()
