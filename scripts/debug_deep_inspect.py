import sqlite3

DB_PATH = "clan_data.db"

def deep_inspect():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    targets = ["kush", "terminat", "p2k", "reagan"]
    
    print("\n--- DEEP INSPECTION ---")
    for t in targets:
        print(f"\nTarget Pattern: '%{t}%'")
        
        # 1. Check Members matching
        cursor.execute(f"SELECT id, username FROM clan_members WHERE username LIKE '%{t}%'")
        members = cursor.fetchall()
        print(f"  Members Found: {members}")
        
        # 2. Check Messages matching name
        cursor.execute(f"SELECT user_id, author_name, COUNT(*) FROM discord_messages WHERE author_name LIKE '%{t}%' GROUP BY user_id, author_name")
        rows = cursor.fetchall()
        print("  Messages Grouped:")
        for r in rows:
            uid = r[0]
            name = r[1]
            cnt = r[2]
            print(f"    - UserID: {uid} | Author: '{name}' | Count: {cnt}")
            
    conn.close()

if __name__ == "__main__":
    deep_inspect()
