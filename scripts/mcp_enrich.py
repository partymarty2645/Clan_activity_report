
import os
import sys
import json
import sqlite3
import logging
import warnings

# Suppress warnings
warnings.filterwarnings("ignore", category=FutureWarning)

from datetime import datetime
from dotenv import load_dotenv

from services.llm_client import UnifiedLLMClient, ModelProvider

# Setup paths
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.config import Config
load_dotenv()

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("mcp_enrich")
ASSET_LIMIT = int(os.getenv("MCP_ASSET_LIMIT", "80"))
RECENT_PLAYER_LIMIT = int(os.getenv("MCP_RECENT_PLAYER_LIMIT", "15"))
ACTIVITY_WINDOW_DAYS = int(os.getenv("MCP_ACTIVITY_DAYS", "7"))

# Get LLM provider: 1=Gemini 3-flash, 2=Gemini 2.5-pro, 3=Groq (default)
LLM_PROVIDER_NUMBER = int(os.getenv("LLM_PROVIDER", "3"))
try:
    LLM_PROVIDER = UnifiedLLMClient.get_provider_by_number(LLM_PROVIDER_NUMBER)
except ValueError as e:
    logger.warning(f"Invalid LLM_PROVIDER: {e}. Defaulting to Groq.")
    LLM_PROVIDER = ModelProvider.GROQ_OSS_120B

llm_client = UnifiedLLMClient(provider=LLM_PROVIDER)

def get_db_connection():
    return sqlite3.connect("clan_data.db")

def fetch_top_performers(limit=10):
    """Fetch top players by Total XP (latest snapshot)."""
    with get_db_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get latest snapshot for each member
        query = """
            SELECT 
                m.username, 
                m.role, 
                s.total_xp, 
                s.total_boss_kills
            FROM clan_members m
            JOIN wom_snapshots s ON m.id = s.user_id
            WHERE s.timestamp = (
                SELECT MAX(timestamp) 
                FROM wom_snapshots 
                WHERE user_id = m.id
            )
            ORDER BY s.total_xp DESC
            LIMIT ?
        """
        rows = cursor.execute(query, (limit,)).fetchall()
        return [dict(r) for r in rows]

def fetch_recent_active_players(limit=15, days=7):
    """Pick up to `limit` players with snapshots in the last `days`."""
    cutoff = f"-" + str(days) + " days"
    with get_db_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        query = """
            WITH recent AS (
                SELECT *, ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY timestamp DESC) AS rn
                FROM wom_snapshots
                WHERE timestamp >= datetime('now', ?)
            )
            SELECT
                m.username,
                m.role,
                r.total_xp,
                r.total_boss_kills
            FROM recent r
            JOIN clan_members m ON m.id = r.user_id
            WHERE r.rn = 1
            ORDER BY RANDOM()
            LIMIT ?
        """
        rows = cursor.execute(query, (cutoff, limit)).fetchall()
        return [dict(r) for r in rows]

def generate_insights(players):
    """Call Groq API to generate creative insights."""

    def summarize_players(players):
        if not players:
            return "No recent players available."
        def fmt(num):
            return f"{num:,}" if isinstance(num, int) or isinstance(num, float) else str(num)
        xp_sorted = sorted(players, key=lambda record: record.get("total_xp", 0), reverse=True)
        boss_sorted = sorted(players, key=lambda record: record.get("total_boss_kills", 0), reverse=True)
        high_xp = xp_sorted[0]
        high_boss = boss_sorted[0]
        low_xp = xp_sorted[-1]
        avg_xp = sum(record.get("total_xp", 0) for record in players) // len(players)
        avg_boss = sum(record.get("total_boss_kills", 0) for record in players) // len(players)
        highlights = [
            f"Top XP hero: {high_xp.get('username')} ({fmt(high_xp.get('total_xp'))} XP)",
            f"Boss monster: {high_boss.get('username')} ({fmt(high_boss.get('total_boss_kills'))} boss kills)",
            f"Low XP outlier: {low_xp.get('username')} ({fmt(low_xp.get('total_xp'))} XP) is still active", 
            f"Typical snapshot: avg {fmt(avg_xp)} XP, avg {fmt(avg_boss)} boss kills across {len(players)} players",
        ]
        return "\n        ".join(highlights)

    def get_available_assets():
        """Scan assets directory for valid images, then limit the set."""
        assets_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
        try:
            files = sorted(
                f for f in os.listdir(assets_dir)
                if f.endswith(".png") and (f.startswith("boss_") or f.startswith("skill_") or f.startswith("rank_"))
            )
            # Return a tight subset to keep payload small.
            return files[:ASSET_LIMIT]
        except Exception as e:
            logger.warning(f"Could not scan assets: {e}")
            return []

    try:
        logger.info(f"Using {LLM_PROVIDER.value} for AI insights.")
        assets = get_available_assets()
        asset_summary = "A rotating pool of boss, skill, and rank icons (patterns: boss_*, skill_*, rank_*)."
        
        # Build detailed player breakdown (not just summary)
        player_detail = "\n".join([
            f"- {p.get('username', 'Unknown')}: {p.get('total_xp', 0):,} XP, {p.get('total_boss_kills', 0):,} boss kills"
            for p in players
        ])
        
        player_summary = summarize_players(players)
        
        # Load Clan Lore / Context
        lore_content = ""
        lore_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "clan_lore.md")
        try:
            if os.path.exists(lore_path):
                with open(lore_path, "r", encoding="utf-8") as f:
                    lore_content = f.read()
        except Exception as e:
            logger.warning(f"Could not load clan_lore.md: {e}")

        # Build detailed player data with individual stats and ratios
        player_detail = "\n".join([
            f"  {i+1}. {p.get('username', 'Unknown')}: {p.get('total_xp', 0):,} XP, {p.get('total_boss_kills', 0):,} boss kills"
            for i, p in enumerate(players)
        ])
        
        # Categorize assets for guided selection
        skill_assets = [a for a in assets if a.startswith('skill_')]
        boss_assets = [a for a in assets if a.startswith('boss_') and not any(x in a.lower() for x in ['event', 'easter', 'christmas', 'halloween'])]
        rank_assets = [a for a in assets if a.startswith('rank_')]
        
        prompt = f"""
        You are the Clan Chronicler for an Old School RuneScape clan (The 0ld G4ng).
        Your ONLY source of truth is the player data provided. DO NOT INVENT ANY FACTS.
        
        **Clan Context:**
        {lore_content}
        
        **CRITICAL CONSTRAINTS:**
        1. ONLY use facts from player data below - ZERO INVENTIONS OR HALLUCINATIONS
        2. If data doesn't support a claim, SKIP THAT INSIGHT
        3. Each insight must reference specific player(s) by name with exact numbers
        4. Maximum 15 words per insight message
        5. **MUST use DIFFERENT image for each insight - NO REPEATS EVER**
        
        **PLAYER DATA (Your ONLY Source of Truth):**
        {player_detail}
        
        **Available Assets** (pick diverse images, rotate through types):
        Skills (for XP/training/efficiency stories): {json.dumps(skill_assets)}
        Bosses (for combat achievements): {json.dumps(boss_assets)}
        Ranks (for milestone/achievement stories): {json.dumps(rank_assets)}
        
        **Asset Selection Strategy - CRITICAL:**
        - EACH insight MUST use a DIFFERENT image (never repeat an image)
        - Skill stories → skill_*.png images
        - Combat/boss stories → different boss_*.png images each time
        - Rank/achievement stories → rank_*.png images
        - Constantly rotate through the asset pool
        - **Failing to diversify images is a critical failure**
        
        **CLAN LEADERSHIP (Real Ranks):**
        - Owner: partymarty94 (463,868,162 XP, 25,178 boss kills)
        - Zenyte #1: jakestl314 (304,525,690 XP, 6,316 boss kills)
        - Zenyte #2: psilocyn (233,340,137 XP, 693 boss kills)
        
        **DEPUTY OWNERS (Second Tier Leadership):**
        - docofmed: 284,606,730 XP, 14,846 kills (closest to owner XP, strong combat)
        - jbwell: 123,711,404 XP, 6,226 kills (structural leader)
        - mtndck: 110,214,258 XP, 4,103 kills (solid grinder)
        
        **SAVIOUR TIER (Third Tier Leadership):**
        - wonindstink: 207,176,259 XP, 11,221 kills (high combat achievement)
        - sirgowi: 138,688,845 XP, 4,060 kills (spiritual contributor)
        
        **KEY CONTRIBUTING ACHIEVER:**
        - vanvolterii: 161,376,505 XP, 8,912 kills (significant contributor)
        
        **Leadership Context:**
        - partymarty94 (Owner) leads by 52% over first zenyte
        - Owner + 2 Zenytes = Leadership Trio
        - 3 Deputy Owners form secondary leadership tier
        - 2 Saviours represent third structural tier
        - These 9 players (7 + 2 new) define clan's power structure and governance
        
        **Your Mission:**
        1. FEATURE ONLY THE 9 LEADERS listed above
        2. Create 10-11 narratives exclusively about:
           - Owner: partymarty94 and their unmatched dominance
           - Zenytes: jakestl314 and psilocyn roles and contrast
           - Deputy Owners: docofmed, jbwell, and mtndck as structural leaders
           - Saviours: wonindstink and sirgowi as third tier (high combat + spiritual)
           - Comparative hierarchies showing tier positioning
           - Why these 9 specifically matter to clan structure and governance
        3. Asset diversity: Use different image for EACH insight (no repeats)
        4. Message format variety across all insights (never use same template)
        5. Focus on: RANK + ROLE + ACHIEVEMENT = CLAN IMPORTANCE
        6. ZERO secondary players - only reference the named 9 leaders
        
        **Output Rules:**
        - Return ONLY valid JSON array with no markdown blocks
        - Each object: {{"type": "...", "title": "...", "message": "...", "image": "...", "icon": "..."}}
        - Types: trend, milestone, fun, battle, outlier
        - **EVERY IMAGE MUST BE DIFFERENT - This is mandatory**
        - **ONLY factual claims using real player names and numbers from data above**
        - **MESSAGE FORMAT VARIETY** (do NOT use same template for all):
          * Comparative: "PlayerA leads with X vs PlayerB's Y"
          * Narrative: "From humble starts, PlayerX now dominates with..."
          * Question format: "Who holds the throne? PlayerX with..."
          * Challenge: "Can anyone match PlayerX's X achievement?"
          * Superlative: "The fastest grinder, highest killer, strongest force..."
          * Stat-driven: "Numbers tell the story: PlayerX stands at..."
        - Example varied formats:
          * {{"type": "battle", "title": "The Reigning Tyrant", "message": "PlayerX's 50,000 kills reign supreme", "image": "...", "icon": "⚔️"}}
          * {{"type": "milestone", "title": "Unmatched Climb", "message": "Who reaches 600M XP? Only PlayerY has ascended this high", "image": "...", "icon": "🏆"}}
          * {{"type": "trend", "title": "The Grind Never Stops", "message": "PlayerZ's relentless pace: 30K kills in a snapshot window", "image": "...", "icon": "📈"}}
        """
        
        logger.info(f"Sending request to {LLM_PROVIDER.value} API (Payload: {len(players)} players, Assets: {len(assets)})...")
        response = llm_client.generate(
            prompt,
            max_tokens=8192,
            temperature=1,
        )
        
        # Clean response (remove potential markdown blocks)
        text = response.content.replace("```json", "").replace("```", "").strip()
        insights = json.loads(text)
        
        logger.info(f"Generated {len(insights)} insights.")
        return insights

    except Exception as e:
        logger.error(f"LLM API Error: {e}")
        print(f"DEBUG_ERR: {e}", flush=True)
        return []

def main():
    
    logger.info("--- Starting AI Enrichment ---")
    
    # 1. Read Data (Local SQLite) - Expanded to 75 as requested
    players = fetch_recent_active_players(RECENT_PLAYER_LIMIT, ACTIVITY_WINDOW_DAYS)
    print(f"DEBUG: Fetched {len(players)} players active in the last {ACTIVITY_WINDOW_DAYS} days.", flush=True)
    if not players:
        logger.warning("No active players found to analyze.")
        return

    # 2. Analyze (Groq API)
    insights = generate_insights(players)
    
    # 3. Export (JSON)
    if insights:
        output_path = os.path.join("data", "ai_insights.json")
        os.makedirs("data", exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(insights, f, indent=2)
            
        logger.info(f"Saved insights to {output_path}")
    else:
        logger.warning("No insights generated.")

if __name__ == "__main__":
    main()
