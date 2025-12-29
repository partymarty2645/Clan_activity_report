import sqlite3
import pandas as pd
from core.usernames import UsernameNormalizer

DB_PATH = "clan_data.db"

def inspect_user():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check clan_members
    print("--- Clan Members (Search 'batgang') ---")
    cursor.execute("SELECT id, username, discord_id FROM clan_members WHERE username LIKE '%batgang%'")
    rows = cursor.fetchall()
    for r in rows:
        print(r)
        
    # Check Messages
    print("\n--- Discord Messages (Search 'batgang') ---")
    cursor.execute("SELECT author_id, author_name, COUNT(*) FROM discord_messages WHERE author_name LIKE '%batgang%' GROUP BY author_id, author_name")
    rows = cursor.fetchall()
    for r in rows:
        print(r)

    conn.close()

if __name__ == "__main__":
    inspect_user()
