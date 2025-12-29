import sqlite3
import pandas as pd

DB_PATH = "clan_data.db"

def inspect_schema():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    print("Tables:", [r[0] for r in cursor.fetchall()])
    
    # Check clan_members columns
    print("\n--- clan_members Columns ---")
    cursor.execute("PRAGMA table_info(clan_members)")
    for c in cursor.fetchall():
        print(c)

    # Check discord_messages columns
    print("\n--- discord_messages Columns ---")
    cursor.execute("PRAGMA table_info(discord_messages)")
    for c in cursor.fetchall():
        print(c)

    # Check actual data for Batgang
    print("\n--- Data Linkage Check ---")
    # Member ID for Batgang
    cursor.execute("SELECT id, username FROM clan_members WHERE username LIKE '%batgang%'")
    members = cursor.fetchall()
    print("Members found:", members)
    
    if members:
        mid = members[0][0]
        # Messages linked to this ID
        cursor.execute(f"SELECT COUNT(*) FROM discord_messages WHERE user_id = {mid}")
        print(f"Messages linked to ID {mid}: {cursor.fetchone()[0]}")
        
    # Inspect Specific Users
    targets = ["solo", "erect", "volter"]
    
    print("\n--- Targeted Inspection ---")
    for t in targets:
        print(f"\nSEARCH: '{t}'")
        
        # Check Members
        cursor.execute(f"SELECT id, username FROM clan_members WHERE username LIKE '%{t}%'")
        members = cursor.fetchall()
        print(f"  > Members ({len(members)}):")
        for m in members:
            # Check linking
            cursor.execute(f"SELECT COUNT(*) FROM discord_messages WHERE user_id = {m[0]}")
            cnt = cursor.fetchone()[0]
            print(f"    - ID {m[0]}: '{m[1]}' (Linked Msgs: {cnt})")
        
        # Check Unlinked Messages
        cursor.execute(f"SELECT COUNT(*), author_name FROM discord_messages WHERE author_name LIKE '%{t}%' AND user_id IS NULL GROUP BY author_name")
        unlinked = cursor.fetchall()
        print(f"  > Unlinked Messages:")
        for u in unlinked:
            print(f"    - '{u[1]}': {u[0]} msgs")


    conn.close()

if __name__ == "__main__":
    inspect_schema()
