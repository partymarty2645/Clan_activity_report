
import sqlite3
import re
from collections import Counter
from datetime import datetime, timezone

# --- CONFIG (Mirroring main.py) ---
DB_PATH = 'clan_data.db'
REGEX_BRIDGE = r"\*\*([^\*]+)\*\*"

# Define Stop Words (Common + Bot/Jargon + IDs)
# Keeping: lol, gz, lmao, ty, haha, yeah
STOP_WORDS = {
    # Standard Grammar
    'the', 'a', 'an', 'and', 'but', 'or', 'if', 'because', 'as', 'what',
    'when', 'where', 'how', 'who', 'why', 'which', 'this', 'that', 'these', 'those',
    'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did',
    'i', 'me', 'my', 'mine', 'you', 'your', 'yours', 'he', 'him', 'his', 'she', 'her', 'hers',
    'it', 'its', 'we', 'us', 'our', 'ours', 'they', 'them', 'their', 'theirs',
    'to', 'from', 'in', 'on', 'at', 'by', 'for', 'with', 'about', 'against', 'between', 'into', 'through',
    'during', 'before', 'after', 'above', 'below', 'to', 'from', 'up', 'down', 'out', 'off', 'over', 'under', 'of',
    'again', 'further', 'then', 'once', 'here', 'there', 'all', 'any', 'both', 'each', 'few', 'more',
    'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very',
    's', 't', 'can', 'will', 'just', 'don', 'should', 'now', 'd', 'll', 'm', 'o', 're', 've', 'y', 'ain', 'aren',
    'could', 'didn', 'doesn', 'hadn', 'hasn', 'haven', 'isn', 'ma', 'might', 'must', 'need', 'shan', 'shouldn',
    'wasn', 'weren', 'won', 'wouldn', 'im', 'u', 'dont', 'cant', 'thats', 'didnt', 'whats', 'theres', 'got', 'get',
    'like', 'one', 'good', 'bad', 'well', 'going', 'know', 'think', 'see', 'say', 'look', 'make', 'go', 'come',
    'take', 'want', 'give', 'use', 'find', 'tell', 'ask', 'work', 'seem', 'feel', 'try', 'leave', 'call',
    
    # Bot & Game Jargon (Specific Exclusions)
    'bot', 'statsicon', 'combatachievementsicon',
    'ironman_chat_badge', 'group_ironman_chat_badge', 'bountyhuntertradericon', 'speedrunningshopicon',
    'gnome_child', 'http', 'https', 'www', 'com', 'scams',
    
    # Ranks (User Provided List + Common)
    'prospector', 'spellcaster', 'astral', 'wintumber', 'therapist', 'saviour', 'wrath', 
    'apothecary', 'dragonstone', 'tztok', 'slayer', 'owner', 'wild', 'doctor', 'runecrafter', 
    'bob', 'deputy_owner', 'hellcat', 'short_green_guy', 'artillery', 'smiter', 'zamorakian', 
    'gamer', 'prodigy', 'zenyte', 'dragon', 'administrator', 'member', 'guest', 'smile', 
    'recruited', 'role', 'rank', 'score', 'messages', 'gained', 'total', 'unknown',
    
    # Numbers/IDs
    '1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '000'
}

# "Auto-Announcement" keywords - if message contains these, skip it entirely (it's not user chat)
# These often appear in "User has achieved..." or "User received a drop..." messages
AUTO_ANNOUNCEMENT_TRIGGERS = [
    'received', 'completed', 'reached', 'log', 'collection', 'loot', 'burnt', 'level', 
    'maxed', 'coins', 'xp', 'kill', 'kills', 'kc', 'combat', 'achievements', 'valuable drop', 'achieved'
]

# Whitelist to protect slang even if they end up in stop lists somehow (safety)
ALLOWED_SLANG = {'lol', 'gz', 'lmao', 'ty', 'haha', 'yeah', 'gzz', 'gzzz', 'tyvm'}

def get_member_stopwords():
    """Fetches all member usernames from DB and properly tokenizes them for blocking."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT username FROM wom_snapshots")
        names = [r[0] for r in cursor.fetchall()]
        conn.close()
        
        username_tokens = set()
        for name in names:
            if not name: continue
            # Normalize: "Sir Gowi" -> "sir gowi"
            norm = name.lower()
            
            # 1. Block the full joined thing if it was one token (e.g. partymarty94)
            username_tokens.add(norm)
            
            # 2. Block parts (e.g. "sir", "gowi")
            parts = re.split(r'[^\w]', norm)
            for p in parts:
                if len(p) > 2: # Avoid blocking 'a', 'i', 'me' if they appear in names? (unlikely but safe)
                    username_tokens.add(p)
                    
        return username_tokens
    except Exception as e:
        print(f"Error fetching members: {e}")
        return set()

def analyze_words():
    print("Connecting to DB...")
    
    # 0. Load Dynamic Stop Words (Usernames)
    member_stops = get_member_stopwords()
    print(f"Loaded {len(member_stops)} username tokens to block (e.g. {list(member_stops)[:5]})")
    
    combined_stops = STOP_WORDS.union(member_stops)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Fetch all messages (mimicking global analysis)
    cursor.execute("SELECT content FROM discord_messages")
    rows = cursor.fetchall()
    
    print(f"Analyzing {len(rows)} messages...")
    
    word_counter = Counter()
    regex_bridge = re.compile(REGEX_BRIDGE)
    
    processed_count = 0
    skipped_system_count = 0
    
    for row in rows:
        content = row['content'] or ""
        if not content: continue
        
        message_body = content # Default
        
        # Check Bridge parsing (mimic main.py logic)
        matches = regex_bridge.findall(content)
        if matches:
             # Bridge message detected: "**User**: Message" or "**User** (Rank): Message"
             # Split on first colon
             parts = content.split(':', 1)
             if len(parts) > 1:
                 message_body = parts[1].strip()
             else:
                 message_body = ""

        if not message_body:
            continue
            
        # Filter "Auto-Announcements"
        msg_lower = message_body.lower()
        if any(trigger in msg_lower for trigger in AUTO_ANNOUNCEMENT_TRIGGERS):
            skipped_system_count += 1
            continue

        processed_count += 1
        
        # Tokenize & Filter
        clean_text = re.sub(r'[^\w\s]', ' ', msg_lower)
        words = clean_text.split()
        
        valid_words = []
        for w in words:
            if w.isdigit(): continue
            if w not in ALLOWED_SLANG and (w in combined_stops or len(w) < 2):
                continue
            valid_words.append(w)
            
        word_counter.update(valid_words)
        
    conn.close()
    
    print(f"Processed {processed_count} user messages (Skipped {skipped_system_count} system messages).")
    
    # Get Top 200
    top_words = word_counter.most_common(200)
    
    # Write to file
    with open('words_report.txt', 'w', encoding='utf-8') as f:
        f.write("--- Top Most Frequent Words (FILTERED) ---\n")
        f.write(f"Based on {processed_count} messages analyzed.\n\n")
        
        for i, (word, count) in enumerate(top_words, 1):
            f.write(f"{i}. {word} ({count})\n")
            
    print("Analysis saved to words_report.txt")

if __name__ == "__main__":
    analyze_words()
