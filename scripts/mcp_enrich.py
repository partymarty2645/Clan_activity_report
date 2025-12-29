
import os
import sys
import json
import sqlite3
import logging
import warnings
import random
import time

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
    """Pick up to `limit` players with snapshots in the last `days`, including Discord message count and join date."""
    cutoff = f"-" + str(days) + " days"
    with get_db_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        query = """
            WITH recent AS (
                SELECT *, ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY timestamp DESC) AS rn
                FROM wom_snapshots
                WHERE timestamp >= datetime('now', ?)
            ),
            message_counts AS (
                SELECT author_name, COUNT(*) as total_messages
                FROM discord_messages
                GROUP BY author_name
            )
            SELECT
                m.username,
                m.role,
                m.joined_at,
                r.total_xp,
                r.total_boss_kills,
                COALESCE(mc.total_messages, 0) as total_messages
            FROM recent r
            JOIN clan_members m ON m.id = r.user_id
            LEFT JOIN message_counts mc ON mc.author_name = m.username
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
        """Scan assets directory for valid images, then randomly sample to avoid bias."""
        assets_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
        try:
            files = [f for f in os.listdir(assets_dir)
                    if f.endswith(".png") and (f.startswith("boss_") or f.startswith("skill_") or f.startswith("rank_"))]
            # Use random.sample to get a truly randomized subset, avoiding alphabetical bias
            # random.sample returns a list of unique random choices from the population
            if not files:
                return []
            num_to_select = min(ASSET_LIMIT, len(files))
            return random.sample(files, num_to_select)
        except Exception as e:
            logger.warning(f"Could not scan assets: {e}")
            return []
    
    def load_assets():
        """Load curated bosses, skills, and ranks from data/assets.json."""
        asset_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "assets.json")
        try:
            if os.path.exists(asset_path):
                with open(asset_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load assets: {e}")
        return {"bosses": [], "skills": [], "ranks": {}}

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

        # Build detailed player data with individual stats, messages, and join date
        def format_join_date(joined_at):
            """Format join date as days ago."""
            if not joined_at:
                return "unknown join date"
            try:
                from datetime import datetime
                join_dt = datetime.fromisoformat(joined_at.replace('Z', '+00:00')) if isinstance(joined_at, str) else joined_at
                now = datetime.now(join_dt.tzinfo) if join_dt.tzinfo else datetime.now()
                days_ago = (now - join_dt).days
                return f"joined {days_ago}d ago" if days_ago > 0 else "recently joined"
            except:
                return "unknown"
        
        player_detail = "\n".join([
            f"  {i+1}. {p.get('username', 'Unknown')}: {p.get('total_xp', 0):,} XP, {p.get('total_boss_kills', 0):,} boss kills, {p.get('total_messages', 0):,} messages ({format_join_date(p.get('joined_at'))})"
            for i, p in enumerate(players)
        ])
        
        # Load curated assets (bosses, skills, ranks) - PROVIDE ALL to avoid asset mismatch
        all_assets = load_assets()
        bosses_all = all_assets.get("bosses", [])  # All 79 bosses
        skills_all = all_assets.get("skills", [])  # All 24 skills
        
        # Flatten all ranks for easy reference
        ranks_all = []
        for rank_category in all_assets.get("ranks", {}).values():
            if isinstance(rank_category, list):
                ranks_all.extend(rank_category)
        # ranks_all now contains all 270 ranks
        
        skill_assets = [a for a in assets if a.startswith('skill_')]
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
        Skills (for XP/training/efficiency stories): {', '.join(skills_all)}
        Bosses (for combat achievements): {', '.join(bosses_all)}
        Clan Ranks (for progression/role stories): {', '.join(ranks_all)}
        Ranks (for milestone/achievement stories): rank_*.png files
        
        **Asset Selection Strategy - CRITICAL:**
        - ALL 79 bosses, ALL 24 skills, and ALL 270 ranks are available
        - EACH insight MUST use a DIFFERENT image (never repeat an image)
        - Skill stories → Pick skill_*.png images (e.g., Slayer, Mining, Ranged)
        - Combat/boss stories → Pick different boss_*.png images each time (e.g., Tekton, Vorkath, Verzik)
        - Rank/achievement stories → Pick rank_*.png images (e.g., Owner, Deputy, Zenyte, Sapphire)
        - Match asset to narrative: If player dominates Slayer, use Slayer skill icon; if Owner rank, use Owner icon
        - Constantly rotate through the complete asset pool to ensure variety
        - **Failing to diversify images or matching narrative to assets is a critical failure**
        
        **KEY INSIGHT: Apply The Golden Rule**
        Messages > Boss KC > XP. A chatter is worth more than a grinder. Look for Yappers (high messages).
        
        **Top Leaders by Rank (from Lore):**
        - Owner: partymarty94 (dev, codes, hates agility)
        - Deputy-owners: docofmed (The Golden Boy - high XP/KC/Messages), jbwell, mtndck
        - Zenytes: jakestl314, psilocyn (both moderators, equal in hierarchy)
        
        **Your Mission (Apply Clan Lore):**
        1. Apply the Golden Rule: **Messages > Boss KC > XP** - Chatters/Yappers are THE heart of the clan
           * Look for players with HIGH MESSAGE COUNTS - they're more valuable than silent grinders
           * Reference "Yappers" (high messages) vs "Ghosts" (silent but skilled)
           * Celebrate both types but acknowledge the social value
        2. Analyze Seniority: Use join dates to identify "Old Guard" (veteran roasters) vs new members
           * Recently joined = newbies, celebrate their early progress
           * Long-time members = veterans, acknowledge their consistency
        3. Spot Rising Stars: Players with good message count + respectable KC/XP combo
        4. Use Clan Terminology: "Spoon" (blessed by RNG), "Dry" (testing faith), "The Grind" (meditative respect)
        5. Reference Nicknames & Personas from lore when applicable (e.g., "The Golden Boy" = docofmed)
        6. Create 3 leadership insights: Focus on top performers (high messages OR high KC)
        7. Create 3 supporting insights: Rising stars, newly joined, or specialized achievements
        8. Keep language chill and irreverent matching clan's "banter, a lot" vibe
        
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
        
        **FINAL INSTRUCTION:**
        Create exactly 6 insights in ONE response:
        - 3 leadership insights (Owner, Deputy Owners, Zenytes)
        - 3 supporting player insights (rising stars, ducklings, specialists)
        
        Return ONLY a valid JSON array with 6 objects. No markdown blocks. No explanations.
        """
        
        logger.info(f"Sending unified request to {LLM_PROVIDER.value} API (6 insights: 3 leadership + 3 supporting)...")
        response = llm_client.generate(
            prompt,
            max_tokens=4096,
            temperature=1,
        )
        
        # Parse response
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
