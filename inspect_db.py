import sqlite3
import json

def inspect_raw():
    try:
        conn = sqlite3.connect('e:/Clan_activity_report/clan_data.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT raw_data FROM wom_snapshots LIMIT 1")
        row = cursor.fetchone()
        if row and row['raw_data']:
            try:
                data = json.loads(row['raw_data'])
                if 'latestSnapshot' in data:
                    snapshot = data['latestSnapshot']
                    if 'data' in snapshot and 'bosses' in snapshot['data']:
                         bosses = snapshot['data']['bosses']
                         print("ALL Boss keys:", list(bosses.keys()))
            except json.JSONDecodeError:
                print("Failed to decode JSON")
        else:
            print("No raw data found")
        conn.close()
    except Exception as e:
        print(e)

if __name__ == "__main__":
    inspect_raw()
