import sys
import os
import json
import sqlite3
import random
import time
import logging
from typing import List, Dict, Any, Optional, Tuple
import datetime

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
ACTIVITY_WINDOW_DAYS = Config.AI_ACTIVITY_DAYS
RECENT_PLAYER_LIMIT = 50 # Send top 50 active players to AI context

# Use Standardized Enum from llm_client.py
LLM_PROVIDER = ModelProvider.GEMINI_FLASH_LITE
OUTPUT_JSON_FILE = "data/ai_insights.json"
OUTPUT_JS_FILE = "docs/ai_data.js"

# --- SYSTEM PROMPT & COMMANDMENTS ---
SYSTEM_PROMPT = """
You are Clank, the sarcastic, witty, and mathematically precise clan droid for the 'Batgang' OSRS clan.
Your job is to analyze clan data and generate brief, engaging "Insights" for the dashboard.

THE 12 COMMANDMENTS (STRICT RULES):
1. **Accuracy First**: Never hallucinate numbers. If Player A has 100 kills and Player B has 50, strictly state A > B.
2. **Logic Check**: Verify comparisons. 1212 is NOT greater than 2115.
3. **Leadership Whitelist**: Only recognize these users as Staff/Leadership: {leadership_roster}. Everyone else is a 'Member'.
4. **Roast Logic**: 
   - High Stats (Active) -> "Touch Grass", "Sweaty", "Machine".
   - High XP but 0 Messages -> "Silent Grinder", "Bot??".
   - Low Stats but High Messages -> "Social Butterfly", "XP Waste".
   - 0 Stats AND 0 Messages -> IGNORE (Do not roast inactive/dead accounts).
5. **No Fake Milestones**: Do not claim "Level 99" unless explicitly shown in data. Stick to "Huge XP gains".
6. **Tone**: Casual, gamer slang (spooned, dry, planked, gz), slightly chaotic but friendly.
7. **Brevity**: Messages must be SHORT (under 120 chars if possible) to fit on cards.
8. **Format**: Output MUST be valid JSON list of objects.
9. **Variety**: Mix types: 'milestone', 'roast', 'trend', 'leadership', 'fun'.
10. **Icons**: Use FontAwesome class names (e.g., 'fa-trophy', 'fa-skull', 'fa-comment').
11. **Specifics**: Use exact numbers from the data. "User gained 1.5M XP", not "User gained a lot of XP".
12. **No Generic Praise**: Avoid "Good job everyone". Highlight specific feats.
"""

def get_db_connection():
    return sqlite3.connect(Config.DB_FILE)

def get_leadership_roster() -> List[str]:
    """Load leadership roster from clan member role data."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT username 
            FROM clan_members 
            WHERE role IN ('Owner', 'Deputy Owner', 'Leader', 'Admin', 'Moderator', 'Organiser')
            ORDER BY role, username
        """)
        leadership = [row[0] for row in cursor.fetchall()]
        conn.close()
        if not leadership:
             return ["Partymarty2645"]
        return leadership
    except Exception as e:
        logger.warning(f"Failed to load leadership roster: {e}")
        return ["Partymarty2645"]

def get_trend_context(cursor) -> str:
    """Get trend context information for AI generation."""
    try:
        # Get recent activity trends
        cursor.execute(f"""
            SELECT COUNT(*) as msg_count, 
                   COUNT(DISTINCT author_name) as unique_authors
            FROM discord_messages 
            WHERE created_at >= date('now', '-{ACTIVITY_WINDOW_DAYS} days')
        """)
        msg_data = cursor.fetchone()
        
        cursor.execute(f"""
            SELECT COUNT(*) as snap_count,
            COUNT(DISTINCT username) as unique_users
            FROM wom_snapshots 
            WHERE timestamp >= date('now', '-{ACTIVITY_WINDOW_DAYS} days')
        """)
        snap_data = cursor.fetchone()
        
        trend_context = f"Discord: {msg_data[0]} messages from {msg_data[1]} active chatterboxes. " \
                       f"Game: {snap_data[0]} snapshots from {snap_data[1]} active players."
        
        return trend_context
    except Exception as e:
        logger.error(f"Error getting trend context: {e}")
        return "Trend data unavailable"

def fetch_active_players(limit: int = 50) -> Tuple[List[Dict], str, Dict]:
    """
    Fetch ONLY players active in the last {ACTIVITY_WINDOW_DAYS} days.
    Uses UserAccessService for consistent access.
    """
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 1. Get Trend Context
    trend_narrative = get_trend_context(cursor)
    
    # 2. Get Active Players using UserAccessService logic (Embedded for standalone safety)
    # We will use the 'legacy' style query here for robustness/speed in this hotfix script,
    # mirroring the logic viewed in previous robust versions.
    
    players = []
    try:
        cursor.execute(f"""
            SELECT m.username, m.role, m.joined_at,
                   (SELECT total_xp FROM wom_snapshots WHERE username=m.username ORDER BY timestamp DESC LIMIT 1) as total_xp,
                   (SELECT total_boss_kills FROM wom_snapshots WHERE username=m.username ORDER BY timestamp DESC LIMIT 1) as total_boss,
                   (SELECT count(*) FROM discord_messages WHERE author_name=m.username AND created_at > date('now', '-7 days')) as msgs_7d
            FROM clan_members m
        """)
        all_members = [dict(r) for r in cursor.fetchall()]
        
        for m in all_members:
            u = m['username']
            # Get 7d differentials (Simplified)
            cursor.execute(f"""
                SELECT total_xp, total_boss_kills, timestamp 
                FROM wom_snapshots WHERE username=? AND timestamp <= date('now', '-7 days') 
                ORDER BY timestamp DESC LIMIT 1
            """, (u,))
            base = cursor.fetchone()
            
            curr_xp = m['total_xp'] or 0
            curr_boss = m['total_boss'] or 0
            
            if base:
                xp_7d = curr_xp - (base[0] or 0)
                boss_7d = curr_boss - (base[1] or 0)
            else:
                xp_7d = curr_xp # New user?
                boss_7d = curr_boss
            
            # Filter inactive
            if xp_7d < 1000 and boss_7d < 1 and m['msgs_7d'] < 1:
                continue
                
            activity_score = (xp_7d / 1_000_000) + (boss_7d / 10) + (m['msgs_7d'] / 50)
            
            players.append({
                "username": u,
                "role": m['role'],
                "xp_7d": xp_7d,
                "boss_7d": boss_7d,
                "msgs_7d": m['msgs_7d'],
                "total_xp": curr_xp,
                "total_boss": curr_boss,
                "activity_score": activity_score
            })
            
        players.sort(key=lambda x: x['activity_score'], reverse=True)
        active_candidates = players[:limit]
        
    except Exception as e:
        logger.error(f"Error fetching players: {e}")
        active_candidates = []

    conn.close()
    return active_candidates, trend_narrative, {}

def generate_ai_batch(players: List[Dict], trend_context: str, leadership_roster: List[str]) -> List[Dict]:
    """
    Generates the FULL set of insights in one or two calls to the LLM.
    """
    logger.info("Initializing LLM Client...")
    
    try:
        # Initialize Client
        # Attempt to use Flash Lite (Primary)
        llm = LLMClient(provider=LLM_PROVIDER)
        if not llm.client:
            logger.warning("Flash Lite failed, trying Standard Flash.")
            llm = LLMClient(provider=ModelProvider.GEMINI_FLASH)
            
        # Construct Prompt
        roster_str = ", ".join(leadership_roster)
        
        # Serialize top 20 players for context (save tokens)
        context_players = players[:30] 
        player_context = json.dumps(context_players, indent=2)
        
        prompt = f"""
        {SYSTEM_PROMPT.format(leadership_roster=roster_str)}

        **CLAN STATUS**:
        {trend_context}

        **PLAYER DATA (Top 30 Active)**:
        {player_context}

        **TASK**:
        Generate exactly 10 unique insights in a JSON list.
        Include a mix of:
        - 2x 'milestone': Huge XP or Kill gains.
        - 2x 'roast': Funny banter about specific players (e.g. 0 messages but 10M XP).
        - 1x 'trend': Overall clan vibe.
        - 1x 'leadership': Comment on a Staff member (whitelist only).
        - 2x 'general': General observations.
        - 2x 'fun': Random funny stats/facts.

        **OUTPUT FORMAT**:
        [
          {{ "type": "milestone", "title": "...", "message": "...", "icon": "fa-trophy" }},
          ...
        ]
        
        Output stricly JSON. No markdown fencing.
        """
        
        logger.info("Sending Prompt to Gemini...")
        response = llm.generate(prompt, temperature=0.9)
        
        # Parse JSON
        content = response.content.strip()
        # Strip simple markdown if present
        if content.startswith("```json"):
            content = content.replace("```json", "").replace("```", "")
        
        insights = json.loads(content)
        logger.info(f"✅ Generated {len(insights)} insights.")
        return insights
        
    except Exception as e:
        logger.error(f"LLM Generation Failed: {e}", exc_info=True)
        return []

def main():
    logger.info("Starting AI Analyst (Restored Logic)...")
    
    # 1. Fetch Data
    active_players, trend_context, _ = fetch_active_players(limit=50)
    logger.info(f"Context: {len(active_players)} active players.")
    
    # 2. Get Roster
    roster = get_leadership_roster()
    
    # 3. Generate
    insights = generate_ai_batch(active_players, trend_context, roster)
    
    # 4. Fallback if empty (prevent pipeline fail)
    if not insights:
        logger.warning("Generating Fallback Insights (LLM failed)")
        insights = [
            {"type": "system", "title": "System Active", "message": "AI Cortex is rebooting. Tracking systems operational.", "icon": "fa-server"},
            {"type": "trend", "title": "Activity Detected", "message": f"{len(active_players)} members active recently.", "icon": "fa-chart-line"}
        ]
    
    # 5. Save to JSON (for Export script)
    try:
        os.makedirs(os.path.dirname(OUTPUT_JSON_FILE), exist_ok=True)
        with open(OUTPUT_JSON_FILE, "w", encoding='utf-8') as f:
            json.dump(insights, f, indent=2)
        logger.info(f"Saved {len(insights)} insights to {OUTPUT_JSON_FILE}")
    except Exception as e:
        logger.error(f"Failed to save JSON: {e}")
        
    # 6. Save to JS (for Direct Frontend)
    try:
        os.makedirs(os.path.dirname(OUTPUT_JS_FILE), exist_ok=True)
        # Create a structure compatible with dashboard
        js_payload = {
            "insights": insights,
            "generated_at": datetime.datetime.now().isoformat(),
            "pulse": [i['message'] for i in insights[:5]] # Simple pulse
        }
        with open(OUTPUT_JS_FILE, "w", encoding='utf-8') as f:
            f.write(f"window.aiData = {json.dumps(js_payload, indent=2)};")
        logger.info(f"Saved JS payload to {OUTPUT_JS_FILE}")
    except Exception as e:
        logger.error(f"Failed to save JS: {e}")

if __name__ == "__main__":
    main()