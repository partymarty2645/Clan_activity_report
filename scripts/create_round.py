import argparse
import json
import sqlite3
from services.gemini import generate_character_card

DB_PATH = "clan_data.db"

def fetch_user_context(username):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Get Basic IDs
    cursor.execute("SELECT id FROM clan_members WHERE username LIKE ?", (f"%{username}%",))
    res = cursor.fetchone()
    if not res:
        print(f"User '{username}' not found.")
        return None
    uid = res[0]
    
    # 2. Get Message Count
    cursor.execute("SELECT COUNT(*) FROM discord_messages WHERE user_id = ?", (uid,))
    msg_count = cursor.fetchone()[0]
    
    # Load Identity Map
    import os
    identity_map = {}
    try:
        with open(r"data/identity_map.json", "r") as f:
            identity_map = json.load(f)
    except:
        pass

    # Fallback: Identity Map -> Fuzzy Search
    if msg_count == 0:
        # Check Identity Map first
        if username in identity_map:
            mapped_name = identity_map[username]
            if mapped_name != "SKIP":
                cursor.execute("SELECT count(*) FROM discord_messages WHERE author_name = ?", (mapped_name,))
                msg_count = cursor.fetchone()[0]
                print(f"DEBUG: Used Identity Map {username} -> {mapped_name}: {msg_count} msgs")

        if msg_count == 0:
            cursor.execute("SELECT author_name FROM discord_messages WHERE author_name LIKE ?", (f"%{username}%",))
            fallback_count = len(cursor.fetchall())
            if fallback_count > 0:
                print(f"DEBUG: Found {fallback_count} unlinked messages for {username}. Using fallback count.")
                msg_count = fallback_count
    
    # 3. Get Latest Snapshot for XP/Boss
    cursor.execute("""
        SELECT total_xp, total_boss_kills 
        FROM wom_snapshots 
        WHERE user_id = ? 
        ORDER BY timestamp DESC LIMIT 1
    """, (uid,))
    snap = cursor.fetchone()
    xp = snap[0] if snap else 0
    boss_kills = snap[1] if snap else 0
    
    # 4. Get Top Bosses
    cursor.execute("""
        SELECT boss_name, kills FROM boss_snapshots 
        WHERE snapshot_id = (
             SELECT id FROM wom_snapshots WHERE user_id = ? ORDER BY timestamp DESC LIMIT 1
        )
        ORDER BY kills DESC LIMIT 3
    """, (uid,))
    top_bosses = {row[0]: row[1] for row in cursor.fetchall()}
    
    conn.close()
    
    return {
        "messages": msg_count,
        "total_xp": xp,
        "total_boss_kills": boss_kills,
        "top_bosses": top_bosses
    }

def main():
    parser = argparse.ArgumentParser(description="Generate Round X Card via AI")
    parser.add_argument("--user", required=True, help="Username to analyze")
    args = parser.parse_args()
    
    context = fetch_user_context(args.user)
    if context:
        print(f"Generating card for {args.user} using Flash 2.5+...")
        card = generate_character_card(args.user, context)
        print("\n" + "="*40)
        print(card)
        print("="*40 + "\n")

if __name__ == "__main__":
    main()
