import sqlite3
import argparse
from services.gemini import generate_character_card
import random

DB_PATH = "clan_data.db"

def get_candidates():
    """Selects 10 interesting users based on different criteria."""
    candidates = [] # List of (Category, Username)
    seen_users = set()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    queries = [
        ("The Legend (Top XP)", "SELECT m.username FROM wom_snapshots s JOIN clan_members m ON s.user_id = m.id ORDER BY total_xp DESC LIMIT 1"),
        ("The CEO (Top Boss Kills)", "SELECT m.username FROM wom_snapshots s JOIN clan_members m ON s.user_id = m.id ORDER BY total_boss_kills DESC LIMIT 1"),
        ("The Raider (Top CoX)", "SELECT m.username FROM boss_snapshots b JOIN wom_snapshots s ON b.wom_snapshot_id = s.id JOIN clan_members m ON s.user_id = m.id WHERE b.boss_name = 'chambers_of_xeric' ORDER BY b.kills DESC LIMIT 1"),
        ("The Gold Farmer (Top Vorkath)", "SELECT m.username FROM boss_snapshots b JOIN wom_snapshots s ON b.wom_snapshot_id = s.id JOIN clan_members m ON s.user_id = m.id WHERE b.boss_name = 'vorkath' ORDER BY b.kills DESC LIMIT 1"),
        ("The Nightmare (Top Phosani)", "SELECT m.username FROM boss_snapshots b JOIN wom_snapshots s ON b.wom_snapshot_id = s.id JOIN clan_members m ON s.user_id = m.id WHERE b.boss_name = 'phosanis_nightmare' ORDER BY b.kills DESC LIMIT 1"),
        ("The Chatty One (Top Messages)", "SELECT author_name FROM discord_messages WHERE author_name NOT IN ('osrs clanchat', 'Wise Old Man', 'Clan Mate') GROUP BY author_name ORDER BY count(*) DESC LIMIT 1"),
    ]

    for label, query in queries:
        try:
            cursor.execute(query)
            res = cursor.fetchone()
            if res:
                u = res[0]
                if u not in seen_users:
                    candidates.append((label, u))
                    seen_users.add(u)
        except Exception as e:
            print(f"Error selecting {label}: {e}")

    # Fill the rest with random active members (XP > 10m)
    cursor.execute("SELECT m.username FROM wom_snapshots s JOIN clan_members m ON s.user_id = m.id WHERE total_xp > 10000000 ORDER BY RANDOM() LIMIT 20")
    randoms = cursor.fetchall()
    
    for r in randoms:
        u = r[0]
        if len(candidates) >= 10:
            break
        if u not in seen_users:
            candidates.append(("Random Active Member", u))
            seen_users.add(u)
            
    conn.close()
    return candidates

def fetch_user_context(username):
    """Duplicated context fetcher to ensure isolation."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Get Basic IDs
    cursor.execute("SELECT id FROM clan_members WHERE username LIKE ?", (f"%{username}%",))
    res = cursor.fetchone()
    if not res:
        # Fallback for Discord-only discrepancies
        uid = 0
    else:
        uid = res[0]
    
    # Load Identity Map
    import json
    import os
    identity_map = {}
    try:
        with open(r"data/identity_map.json", "r") as f:
            identity_map = json.load(f)
    except:
        pass

    # 2. Get Message Count (with Identity Map & Fallback)
    if uid:
        cursor.execute("SELECT COUNT(*) FROM discord_messages WHERE user_id = ?", (uid,))
        msg_count = cursor.fetchone()[0]
    else:
        msg_count = 0
        
    if msg_count == 0:
        # Check Identity Map first
        if username in identity_map:
            mapped_name = identity_map[username]
            if mapped_name != "SKIP":
                cursor.execute("SELECT count(*) FROM discord_messages WHERE author_name = ?", (mapped_name,))
                msg_count = cursor.fetchone()[0]
                print(f"DEBUG: Used Identity Map {username} -> {mapped_name}: {msg_count} msgs")
        
        # Fallback to fuzzy match if still 0
        if msg_count == 0:
            cursor.execute("SELECT author_name FROM discord_messages WHERE author_name LIKE ?", (f"%{username}%",))
            fallback_matches = cursor.fetchall()
            if fallback_matches:
                msg_count = len(fallback_matches)
    
    # 3. Get Latest Snapshot for XP/Boss
    xp = 0
    boss_kills = 0
    top_bosses = {}
    
    if uid:
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
    print("Selecting candidates...")
    candidates = get_candidates()
    
    output_md = "# 🧠 AI Feedback Batch #1\n\n"
    from services.gemini import MODEL_NAME
    output_md += f"**Model**: {MODEL_NAME}\n"
    output_md += f"**Objective**: Calibration of Tone and Content.\n\n"
    output_md += "---\n\n"
    
    from services.gemini import generate_bulk_cards

    # 1. Gather all profiles
    profiles = []
    print("Selecting and fetching data for 10 candidates...")
    import time
    
    for category, user in candidates:
        print(f"Fetching context for {user} ({category})...")
        context = fetch_user_context(user)
        profiles.append({
            'username': user,
            'category': category,
            'context': context
        })

    # 2. Bulk Generate
    print(f"Sending BULK request for {len(profiles)} profiles...")
    # 2. Sequential Generate (Testing if Bulk/TPM is the issue)
    print(f"Sending SEQUENTIAL requests for {len(profiles)} profiles (skipping huge bulk)...")
    
    from services.gemini import generate_character_card
    import time

    for p in profiles:
        try:
            print(f"Generating for {p['username']}...")
            card = generate_character_card(p['username'], p['context'])
            
            output_md += f"## Candidate: {p['username']} ({p['category']})\n"
            output_md += f"Context: `{p['context']}`\n\n"
            output_md += card.strip() + "\n\n" 
            output_md += "---\n\n"
            
            # Gentle delay for Rate Limits
            time.sleep(5)
            
        except Exception as e:
            print(f"FAILED for {p['username']}: {e}")
            output_md += f"## FAILURE: {p['username']}\nError: {e}\n\n"
            
    # Skipping Bulk logic for now
    if False:
        bulk_output = generate_bulk_cards(profiles)
        # We asked for ## SCORED_CARD_SEPARATOR separation
        cards = bulk_output.split("## SCORED_CARD_SEPARATOR")
        
        for i, card in enumerate(cards):
            if i < len(profiles):
                p = profiles[i]
                output_md += f"## Candidate: {p['username']} ({p['category']})\n"
                output_md += f"Context: `{p['context']}`\n\n"
                output_md += card.strip() + "\n\n" 
                output_md += "---\n\n"
            else:
                output_md += f"## Extra Card (Index {i})\n\n{card.strip()}\n\n---\n\n"

    # except Exception as e:
    #     print(f"BULK GENERATION FAILED: {e}")
    #     output_md += f"## BULK FAILURE\nError: {e}\n"

    # Save to file
    filename = "reports/ai_feedback_batch_1.md"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(output_md)
    
    print(f"\nBatch generation complete! Saved to {filename}")

if __name__ == "__main__":
    main()
