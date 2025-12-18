import sqlite3

def list_tables():
    conn = sqlite3.connect('e:/Clan_activity_report/clan_data.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("Tables:", [t[0] for t in tables])
    
    for table in tables:
        tname = table[0]
        cursor.execute(f"PRAGMA table_info({tname})")
        columns = cursor.fetchall()
        print(f"\nTable: {tname}")
        for col in columns:
            print(f"  {col[1]} ({col[2]})")

    conn.close()

if __name__ == "__main__":
    list_tables()
