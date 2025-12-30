import sys
import os
import json
import sqlite3
import random
import time
import logging
from typing import List, Dict, Any, Optional

# --- PATH SETUP ---
# Must look two levels up to find 'core' and 'services'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from services.llm_client import UnifiedLLMClient as LLMClient, ModelProvider
    from core.config import Config
except ImportError as e:
    print(f"CRITICAL IMPORT ERROR: {e}")
    # Fallback/Debug print to help user if it still fails
    print(f"Current Sys Path: {sys.path}")
    raise

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("mcp_enrich")

# --- CONFIGURATION ---
DB_PATH = "clan_data.db"
# Use Config for activity window
ACTIVITY_WINDOW_DAYS = 30 # User requested 30 days active window
RECENT_PLAYER_LIMIT = 75  # Increased from 50

# User Priority: 1. Gemini Pro -> 2. Gemini Flash -> 3. Groq (handled by UnifiedLLMClient fallback)
LLM_PROVIDER = ModelProvider.GEMINI_FLASH_LITE

def get_db_connection():
    return sqlite3.connect(DB_PATH)

def load_assets() -> Dict[str, Any]:
    """Load available assets (bosses, skills, ranks) from assets directory."""
    assets_dir = os.path.join("assets")
    assets = {"bosses": [], "skills": [], "ranks": {}}
    
    if not os.path.exists(assets_dir):
        return assets
        
    try:
        # Bosses
        boss_dir = os.path.join(assets_dir, "bosses")
        if os.path.exists(boss_dir):
            assets["bosses"] = [f.replace("boss_", "").replace(".png", "") 
                              for f in os.listdir(boss_dir) if f.endswith(".png")]
            
        # Skills
        skill_dir = os.path.join(assets_dir, "skills")
        if os.path.exists(skill_dir):
            assets["skills"] = [f.replace("skill_", "").replace(".png", "") 
                              for f in os.listdir(skill_dir) if f.endswith(".png")]
            
        # Ranks (map to hierarchy)
        rank_dir = os.path.join(assets_dir, "ranks")
        if os.path.exists(rank_dir):
            # Assume filenames like rank_owner.png, rank_dragonstone.png
            rank_files = [f.replace("rank_", "").replace(".png", "") 
                         for f in os.listdir(rank_dir) if f.endswith(".png")]
            assets["ranks"] = {"general": rank_files} # Simplified handling
            
    except Exception as e:
        logger.warning(f"Could not load assets: {e}")
        
    return assets

def get_trend_context(cursor) -> str:
    """
    Calculate the STRICT analytic trend:
    (Total Msgs Last 7 Days) vs (Total Msgs Prior 7 Days)
    """
    try:
        # Current Week (0-7 days ago)
        # Current Window
        cursor.execute(f"""
            SELECT COUNT(*) 
            FROM discord_messages 
            WHERE created_at >= date('now', '-7 days')
        """)
        current_week = cursor.fetchone()[0] or 0
        
        # Prior Window (Previous Period)
        cursor.execute(f"""
            SELECT COUNT(*) 
            FROM discord_messages 
            WHERE created_at < date('now', '-7 days') 
            AND created_at >= date('now', '-14 days')
        """)
        prior_week = cursor.fetchone()[0] or 0
        
        if prior_week == 0:
            return "Trend: 100% Increase (No prior data)"
            
        diff_pct = ((current_week - prior_week) / prior_week) * 100
        direction = "UP" if diff_pct >= 0 else "DOWN"
        
        return f"TREND_DATA (WEEKLY/7D): Current={current_week}, Prior={prior_week}, Diff={diff_pct:.1f}%, Direction={direction}"
    except Exception as e:
        logger.error(f"Trend Calc Error: {e}")
        return "TREND_DATA: Unavailable"

# Valid Leadership List (Lower case for matching)
LEADERSHIP_ROSTER = [
    "partymarty94", "mtndck", "maakif", "jbwell", 
    "docofmed", "vanvolter ii", "jakestl314", "psilocyn", "sir gowi", "sirgowi"
]

def fetch_active_players(limit: int = 100) -> (List[Dict], str):
    """
    "The 12 Commandments" Filter:
    Fetch ONLY players active in the last {ACTIVITY_WINDOW_DAYS} days.
    Active = XP > 0 OR Kills > 0 OR Messages > 0.
    Returns: (list_of_active_players, trend_narrative, extra_context_dict)
    """
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 1. Get Trend Context
    trend_narrative = get_trend_context(cursor)
    
    players = []
    try:
        # Simple Logic: Get all members, filter in python based on recent snapshots.
        cursor.execute("SELECT username, joined_at, role FROM clan_members")
        all_members = [dict(row) for row in cursor.fetchall()]
        
        active_candidates = []
        
        for m in all_members:
            u = m['username']
            
        for m in all_members:
            u = m['username']
            uid = None
            
            # Resolve Member ID (since snapshots use user_id or likely joined via username if ID missing)
            # Actually wom_snapshots has username column too, let's use that for simplicity and speed (idx exists)
            
            # 1. Get Latest Snapshot
            cursor.execute("""
                SELECT total_xp, total_boss_kills, timestamp 
                FROM wom_snapshots 
                WHERE username = ? 
                ORDER BY timestamp DESC LIMIT 1
            """, (u,))
            latest = cursor.fetchone()
            
            # 2. Get Baseline Snapshot (~14 days ago)
            cursor.execute(f"""
                SELECT total_xp, total_boss_kills 
                FROM wom_snapshots 
                WHERE username = ? 
                AND timestamp <= date('now', '-{ACTIVITY_WINDOW_DAYS} days')
                ORDER BY timestamp DESC LIMIT 1
            """, (u,))
            baseline = cursor.fetchone()
            
            if not latest:
                continue # No data at all for this user
                
            l_xp = latest[0] or 0
            l_boss = latest[1] or 0
            
            if baseline:
                b_xp = baseline[0] or 0
                b_boss = baseline[1] or 0
                xp_gain = max(0, l_xp - b_xp)
                boss_gain = max(0, l_boss - b_boss)
            else:
                # New user (no snapshot older than 14d), so all current stats are "gains" roughly
                # Or we can look for the OLDEST snapshot if it's within 14d
                cursor.execute("""
                    SELECT total_xp, total_boss_kills 
                    FROM wom_snapshots 
                    WHERE username = ? 
                    ORDER BY timestamp ASC LIMIT 1
                """, (u,))
                oldest = cursor.fetchone()
                if oldest:
                    o_xp = oldest[0] or 0
                    o_boss = oldest[1] or 0
                    xp_gain = max(0, l_xp - o_xp)
                    boss_gain = max(0, l_boss - o_boss)
                else:
                     xp_gain = 0
                     boss_gain = 0

            # 3. Messages
            cursor.execute(f"""
                SELECT COUNT(*) FROM discord_messages 
                WHERE author_name = ? AND created_at >= date('now', '-{ACTIVITY_WINDOW_DAYS} days')
            """, (u,))
            msgs = cursor.fetchone()[0] or 0
            
            # 4. Totals
            cursor.execute("SELECT COUNT(*) FROM discord_messages WHERE author_name = ?", (u,))
            total_msgs = cursor.fetchone()[0] or 0
            
            # FILTER: "The Active Gatekeep"
            # 10k XP or 1 Kill or 1 Msg
            if xp_gain < 10000 and boss_gain == 0 and msgs == 0:
                continue 
                
            m['recent_xp'] = xp_gain
            m['recent_kills'] = boss_gain
            m['recent_msgs'] = msgs
            m['total_msgs'] = total_msgs
            
            active_candidates.append(m)
            
        # Sort by "Social Value" (The Golden Rule)
        active_candidates.sort(key=lambda x: (x['recent_msgs'], x['recent_kills'], x['recent_xp']), reverse=True)
        players = active_candidates[:limit]
        
    except Exception as e:
        logger.error(f"Database error: {e}")
    finally:
        conn.close()
    
    # Calculate extra stats
    zero_msg_count = sum(1 for p in all_members if p['username'] not in [ap['username'] for ap in active_candidates if ap.get('recent_msgs', 0) > 0])
    
    extra_context = {
        "zero_msg_count": zero_msg_count,
        "total_members": len(all_members),
        "active_count": len(players)
    }
        
    return players, trend_narrative, extra_context

# User Priority: 1. Gemini Flash-Lite (Production) -> 2. Groq
PROVIDERS = [
    ModelProvider.GEMINI_FLASH_LITE,
    ModelProvider.GROQ_OSS_120B
]

def generate_single_batch(players: List[Dict], trend_context: str, category: str, quantity: int, lore_content: str, extra_context: Dict = {}) -> List[Dict]:
    """Generates a specific batch of insights for a category"""
    logger.info(f"--- Generating Batch: {category.upper()} (Qty: {quantity}) ---")
    
    # Build Stat-Specific Context Strings
    zero_msg_txt = f"{extra_context.get('zero_msg_count', 0)} members sent 0 messages."
    
    # Customize instructions based on category
    category_instructions = {
        "trend": f"Focus ONLY on 'trend' type cards. Analyze WEEKLY trends (Last 7 Days) based on the TREND_DATA context. MUST include exact numbers in message (e.g. 'up by 500 messages').",
        "leadership": f"Focus ONLY on 'leadership' type cards. STRICT RULE: You MUST ONLY select players from this official roster: {LEADERSHIP_ROSTER}. Do NOT assume anyone else is staff. Roast or Praise them based on ACTUAL stats.",
        "roast": "Focus ONLY on 'roast' type cards. Find players with high messages but low XP, or weird boss choices. Roast them. CRITICAL CONTEXT AWARENESS: If a player has HIGH stats (>500 kills OR >10M XP), you can still roast them, but roast them for being a 'sweat', 'no-lifer', or needing to 'touch grass'. DO NOT call their stats low.",
        "spoon": "Focus ONLY on 'spoon' or 'achievement' cards. Highlight big drops or huge XP gains (e.g. > 1M XP). MUST mention the specific XP amount.",
        "general": f"General mix. You can mention that {zero_msg_txt} if relevant ('The Quiet Ones'). Highlight grinders (High XP + Low Msgs).",
        "mixed": f"""
        Generate exactly 10 cards using this distribution: 
        - 2 'trend' (Significant value changes. MUST include numbers like '50% increase' or '+500 msgs').
        - 2 'leadership' (Roast or Praise Owners/Staff based on ACTUAL stats. STRICTLY enforce this list: {LEADERSHIP_ROSTER}. If they are not on this list, they are NOT leadership).
        - 2 'roast' (Funny stats/Banters. CRITICAL: Check the magnitude of stats. High Stats = "Touch Grass" roast. Low Stats = "Slacker" roast. NEVER call >500 kills "low").
        - 2 'milestone' (Replace 'diversity' with specific achievements: e.g., '100M total XP' or 'Top Killer'. DO NOT invent 'Maxed Skill' or 'Level 99' unless you see 13M+ XP in a skill, which you don't have data for, so stick to TOTAL XP milestones).
        - 2 'general' (Interesting observations. Mention '{zero_msg_txt}' as 'The Quiet Observers' if applicable).
        
        CRITICAL RULES:
        1. TIME PERIOD: "Trend" cards use WEEKLY data (7 days). "Player Stats" use {ACTIVITY_WINDOW_DAYS} DAYS. Be clear about this distinction if necessary.
        2. SPECIFICITY: You MUST include the actual stat number in the text. (e.g. "User gained 15M XP", "User sent 400 messages"). Do not just say "huge gains".
        3. HONESTY: Do not claim someone has maxed a skill. Do not claim someone is quiet if they have > 50 messages.
        4. LOGIC CHECK: Ensure your comparisons make sense. If Player A has 2000 messages and Player B has 1000, Player A leads. Do NOT say "Player B leads with 1000 followed by Player A with 2000".
        
        IMPORTANT: Your JSON objects MUST include a "players" field which is a LIST of strings (usernames involved in the insight).
        """
    }
    
    instruction = category_instructions.get(category, "General insights.")

    prompt_lines = [
        "You are the ClanStats AI (Partymarty2645/ClanStats).",
        "Your goal is to generate JSON content for the clan dashboard.",
        f"TASK: Generate exactly {quantity} insight cards.",
        f"ANALYSIS PERIOD: LAST {ACTIVITY_WINDOW_DAYS} DAYS.",
        f"GLOBAL CONTEXT: {zero_msg_txt}",
        f"CATEGORY FOCUS: {instruction}",
        "RETURN FORMAT: A valid JSON Array of objects. Each object MUST have: 'type', 'title', 'message', 'icon', 'players' (list of usernames). No markdown, no text.",
        "",
        "--- CLAN LORE ---",
        lore_content[:2000], 
        "",
        "--- TREND CONTEXT ---",
        trend_context,
         "",
        "--- ACTIVE PLAYERS (Last 30 Days) ---"
    ]
    
    # Add players (Full list is fine for context, 13k chars is ok)
    for p in players:
        prompt_lines.append(json.dumps(p))
        
    prompt = "\n".join(prompt_lines)
    
    # Limit Prompt Size check
    char_count = len(prompt)
    est_tokens = char_count // 4
    logger.info(f"Batch Prompt Size: {char_count} chars (~{est_tokens} tokens)")

    for provider in PROVIDERS:
        try:
            logger.info(f"Sending batch request to AI ({provider.value})...")
            
            # Init client
            current_client = LLMClient(provider=provider)
            
            # Generate
            response = current_client.generate(prompt, temperature=1.0, max_tokens=6000)
            
            # Parsing Logic (Reused from robust fix)
            content = response.content
            start_idx = content.find('[')
            end_idx = content.rfind(']')
            
            cleaned_content = ""
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                cleaned_content = content[start_idx:end_idx+1]
            else:
                # Fallback implementation
                cleaned_content = content.replace("```json", "").replace("```", "").strip()

            data = []
            try:
                data = json.loads(cleaned_content)
            except json.JSONDecodeError as e:
                # Recovery logic
                if e.msg.startswith("Extra data"):
                    try:
                        logger.info(f"Recovering batch from 'Extra data' at pos {e.pos}...")
                        data = json.loads(cleaned_content[:e.pos])
                    except:
                        pass
                
                if not data:
                    logger.error(f"Batch parse failed for {provider}: {e}")
                    continue # Try next provider

            # Normalization: Ensure iterability
            if isinstance(data, dict):
                data = [data]
                
            if isinstance(data, list) and len(data) > 0:
                # Tag provider
                for item in data:
                    item['_provider'] = provider.value
                
                logger.info(f"Batch success ({len(data)} items) with {provider.value}")
                return data
                
        except Exception as e:
            logger.warning(f"Provider {provider.value} failed batch: {e}")
            continue
            
    return []

def generate_insights(players: List[Dict], trend_context: str, extra_context: Dict = {}) -> List[Dict]:
    """Orchestrates the multi-batch generation"""
    
    # Load Lore Once
    try:
        with open("docs/clan_lore.md", "r", encoding="utf-8") as f:
            lore_content = f.read()
    except:
        lore_content = "Clan Lore: We are a casual OSRS clan."

    all_insights = []
    
    # Define Batches: (Category, Quantity)
    # Total = 10 cards (Single Shot Mode via Flash-Lite)
    batches = [
        ("mixed", 10)
    ]
    
    loading_msgs = [
        "Consulting the Wise Old Man...",
    ]
    
    import random
    
    for category, qty in batches:
        # Generate all 10 in one go
        batch_results = generate_single_batch(players, trend_context, category, qty, lore_content, extra_context)
        all_insights.extend(batch_results)
        
    return all_insights


def main():
    logger.info("--- Starting AI Content Revamp (Active Filter Enabled) ---")
    
    # 1. Fetch & Filter
    # 1. Fetch & Filter
    players, trend, extra_context = fetch_active_players(RECENT_PLAYER_LIMIT)
    logger.info(f"Found {len(players)} active players in last {ACTIVITY_WINDOW_DAYS} days.")
    logger.info(f"Trend Context: {trend}")
    
    if not players:
        logger.warning("No active players found! Check database.")
        return

    # 2. Generate
    insights = generate_insights(players, trend, extra_context)
    
    # 3. Save
    if insights:
        os.makedirs("data", exist_ok=True)
        with open("data/ai_insights.json", "w", encoding="utf-8") as f:
            json.dump(insights, f, indent=2)
        
        # FINAL OUTPUT TO JS
        final_data = {
            "insights": insights,
            "pulse": [], # populated by export_sqlite usually, but empty here works
            "active_roster": [p['username'] for p in players],
            "meta": {
                "window_days": ACTIVITY_WINDOW_DAYS,
                "generated_at": time.strftime("%Y-%m-%d %H:%M:%S")
            }
        }
        
        js_path = os.path.join("docs", "ai_data.js")
        with open(js_path, "w", encoding="utf-8") as f:
            f.write(f"window.aiData = {json.dumps(final_data, indent=2)};")
            
        logger.info(f"Successfully generated {len(insights)} insights. Saved to {js_path}")
    else:
        logger.error("No insights generated.")

if __name__ == "__main__":
    main()
