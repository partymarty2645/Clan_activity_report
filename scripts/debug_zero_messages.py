import sqlite3
import difflib

DB_PATH = "clan_data.db"
TARGETS = ["lapislzuli", "kingofmaga", "itscutty", "b1acknoir", "0m0omoomo"]

def debug_users():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print(f"--- Debugging {len(TARGETS)} Users with '0 Messages' ---")
    
    # 1. Get all known discord authors to fuzzy match against
    cursor.execute("SELECT DISTINCT author_name FROM discord_messages")
    all_authors = [r[0] for r in cursor.fetchall()]
    
    for user in TARGETS:
        print(f"\n[?] User: {user}")
        
        # A. Check Clan Member Link
        cursor.execute("SELECT id, username FROM clan_members WHERE username LIKE ?", (f"%{user}%",))
        member = cursor.fetchone()
        if member:
            mid, username = member
            print(f"    - Found in clan_members (ID: {mid}, Username: {username})")
            
            # Check Aliases
            cursor.execute("SELECT normalized_name, canonical_name FROM player_name_aliases WHERE member_id = ?", (mid,))
            aliases = cursor.fetchall()
            print(f"    - Aliases: {aliases}")
        else:
            print(f"    - NOT FOUND in clan_members table.")

        # B. Check Strict Name Match in Messages
        cursor.execute("SELECT count(*) FROM discord_messages WHERE author_name LIKE ?", (f"%{user}%",))
        strict_count = cursor.fetchone()[0]
        print(f"    - Messages by Name (LIKE '%{user}%'): {strict_count}")
        
        # C. Fuzzy Match in Authors
        matches = difflib.get_close_matches(user, all_authors, n=3, cutoff=0.4)
        print(f"    - Fuzzy Matches in Discord Authors: {matches}")
        
        # D. If match found, show count
        if matches:
            best = matches[0]
            cursor.execute("SELECT count(*) FROM discord_messages WHERE author_name = ?", (best,))
            fuzzy_count = cursor.fetchone()[0]
            print(f"      -> Messages for '{best}': {fuzzy_count}")

    conn.close()

if __name__ == "__main__":
    debug_users()
