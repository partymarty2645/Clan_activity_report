import sys
import os
import json
import sqlite3
import random
import time
import logging
from typing import List, Dict, Any, Optional, Tuple

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
# Use Config.DB_FILE instead of hard-coded path
ACTIVITY_WINDOW_DAYS = Config.AI_ACTIVITY_DAYS
RECENT_PLAYER_LIMIT = Config.AI_PLAYER_LIMIT

# User Priority: 1. Gemini Pro -> 2. Gemini Flash -> 3. Groq (handled by UnifiedLLMClient fallback)
LLM_PROVIDER = ModelProvider.GEMINI_2_5_FLASH_LITE

def get_db_connection():
    return sqlite3.connect(Config.DB_FILE)

def load_assets() -> Dict[str, Any]:
    """Load available assets (bosses, skills, ranks) from assets directory."""
    assets_dir = os.path.join("assets")
    assets = {"bosses": [], "skills": [], "ranks": {}}
    
    if not os.path.exists(assets_dir):
        return assets
        
    try:
        # Assets are in root assets/ directory with prefixes (boss_*.png, skill_*.png, rank_*.png)
        for filename in os.listdir(assets_dir):
            if filename.startswith("boss_") and filename.endswith(".png"):
                assets["bosses"].append(filename.replace("boss_", "").replace(".png", ""))
            elif filename.startswith("skill_") and filename.endswith(".png"):
                assets["skills"].append(filename.replace("skill_", "").replace(".png", ""))
            elif filename.startswith("rank_") and filename.endswith(".png"):
                rank_name = filename.replace("rank_", "").replace(".png", "")
                assets["ranks"][rank_name] = filename
    except Exception as e:
        logger.warning(f"Failed to load assets from {assets_dir}: {e}")
    
    return assets

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
        return leadership
    except Exception as e:
        logger.warning(f"Failed to load leadership roster: {e}")
        return ["Partymarty2645"]  # Fallback to known owner

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
        
        trend_context = f"Discord: {msg_data[0]} messages from {msg_data[1]} users. " \
                       f"Game: {snap_data[0]} snapshots from {snap_data[1]} players."
        
        return trend_context
    except Exception as e:
        logger.error(f"Error getting trend context: {e}")
        return "Trend data unavailable"

def fetch_active_players(limit: int = 100) -> Tuple[List[Dict], str, Dict]:
    """
    "The 12 Commandments" Filter:
    Fetch ONLY players active in the last {ACTIVITY_WINDOW_DAYS} days.
    Active = XP > 0 OR Kills > 0 OR Messages > 0.
    Returns: (list_of_active_players, trend_narrative, extra_context_dict)
    
    MIGRATION: Uses UserAccessService for consistent, optimized database access.
    """
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 1. Get Trend Context (still uses legacy approach)
    trend_narrative = get_trend_context(cursor)
    
    # 2. Get Active Players using UserAccessService
    players = []
    try:
        # Initialize unified database access
        from database.connector import SessionLocal
        from services.user_access_service import UserAccessService
        
        session = SessionLocal()
        user_service = UserAccessService(session)
        
        # UNIFIED ACCESS: Get all active members with calculated stats in one query
        all_active_members = user_service.get_all_active_members(days_back=ACTIVITY_WINDOW_DAYS)
        
        logger.info(f"Retrieved {len(all_active_members)} active members via UserAccessService")
        
        for member_stats in all_active_members:
            # Calculate activity metrics for filtering
            activity_score = 0
            
            # XP activity (weighted by 7-day gains)
            xp_7d = member_stats.xp_7d
            if xp_7d > 100_000:  # Meaningful XP gain
                activity_score += min(xp_7d / 1_000_000, 10)  # Max 10 points for XP
            
            # Boss activity (weighted by 7-day kills)
            boss_7d = member_stats.boss_7d  
            if boss_7d > 5:  # Meaningful boss activity
                activity_score += min(boss_7d / 10, 5)  # Max 5 points for bossing
                
            # Message activity (weighted by 7-day messages)
            msgs_7d = member_stats.msgs_7d
            if msgs_7d > 10:  # Meaningful Discord activity
                activity_score += min(msgs_7d / 50, 5)  # Max 5 points for chatting
            
            # Filter for active members (any activity qualifies, lower threshold)
            if activity_score > 0.1:  # Much lower threshold to show more results
                # Get additional profile data for role information
                profile = user_service.get_user_profile(member_stats.user_id)
                
                player_data = {
                    'username': member_stats.username,
                    'role': profile.role if profile else 'Member',
                    'joined_at': profile.joined_at.isoformat() if profile and profile.joined_at else None,
                    'total_xp': member_stats.total_xp,
                    'total_boss': member_stats.total_boss_kills,
                    'xp_7d': xp_7d,
                    'boss_7d': boss_7d,
                    'msgs_7d': msgs_7d,
                    'xp_30d': member_stats.xp_30d,
                    'boss_30d': member_stats.boss_30d,
                    'msgs_30d': member_stats.msgs_30d,
                    'activity_score': round(activity_score, 2),
                    # Legacy format compatibility
                    'recent_xp': xp_7d,
                    'recent_kills': boss_7d,
                    'recent_msgs': msgs_7d
                }
                
                players.append(player_data)
        
        # Sort by activity score (most active first) and apply limit
        players.sort(key=lambda x: x['activity_score'], reverse=True)
        active_candidates = players[:limit]
        
        session.close()
        
        logger.info(f"Identified {len(active_candidates)} active members (activity score > 0.1, limited to {limit})")
        
    except Exception as e:
        logger.error(f"Error using UserAccessService: {e}")
        # Fallback to legacy method if new unified access fails
        logger.warning("Falling back to legacy database access")
        active_candidates = _get_player_context_legacy(cursor, limit)
    
    # 3. Generate Extra Context
    extra_context = {}
    
    # Silent grinders (high activity, no messages)
    silent_grinders = [p['username'] for p in active_candidates 
                      if p.get('recent_msgs', 0) == 0 
                      and (p.get('recent_xp', 0) > 0 or p.get('recent_kills', 0) > 0)]
    
    if silent_grinders:
        extra_context['silent_grinders'] = f"Silent grinders detected: {', '.join(silent_grinders[:5])}"
    
    # High activity members
    high_activity = [p['username'] for p in active_candidates[:10] 
                    if p.get('activity_score', 0) > 5]
    
    if high_activity:
        extra_context['high_activity'] = f"High activity members: {', '.join(high_activity)}"
    
    conn.close()
    return active_candidates, trend_narrative, extra_context


def _get_player_context_legacy(cursor, limit: int) -> List[Dict]:
    """
    Legacy player context method - kept as fallback.
    
    TODO: Remove once UserAccessService migration is fully validated.
    """
    players = []
    try:
        # Legacy individual query approach
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT username, joined_at, role FROM clan_members")
        all_members = [dict(row) for row in cursor.fetchall()]
        
        active_candidates = []
        
        for m in all_members:
            u = m['username']
            
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
            else:
                # If no baseline, assume all activity is recent
                b_xp = 0
                b_boss = 0
                
            recent_xp = l_xp - b_xp
            recent_kills = l_boss - b_boss
            
            # 3. Get Recent Discord Messages
            cursor.execute(f"""
                SELECT COUNT(*) 
                FROM discord_messages 
                WHERE author_name = ? 
                AND created_at > date('now', '-{ACTIVITY_WINDOW_DAYS} days')
            """, (u,))
            recent_msgs_result = cursor.fetchone()
            recent_msgs = recent_msgs_result[0] if recent_msgs_result else 0
            
            # Activity Check: ANY recent activity qualifies
            if recent_xp > 0 or recent_kills > 0 or recent_msgs > 0:
                player_data = {
                    'username': u,
                    'role': m.get('role', 'Member'),
                    'joined_at': m.get('joined_at'),
                    'total_xp': l_xp,
                    'total_boss': l_boss,
                    'recent_xp': recent_xp,
                    'recent_kills': recent_kills,
                    'recent_msgs': recent_msgs,
                    # Compatibility fields for new format
                    'xp_7d': recent_xp,
                    'boss_7d': recent_kills,
                    'msgs_7d': recent_msgs,
                    'activity_score': min(recent_xp / 1_000_000, 10) + 
                                    min(recent_kills / 10, 5) + 
                                    min(recent_msgs / 50, 5)
                }
                active_candidates.append(player_data)
        
        # Sort by activity score and limit
        active_candidates.sort(key=lambda x: x.get('activity_score', 0), reverse=True)
        players = active_candidates[:limit]
        
        conn.close()
        
    except Exception as e:
        logger.error(f"Legacy database error: {e}")
        
    return players


# User Priority: 1. Flash (Primary) -> 2. Flash-Lite (Fallback) -> 3. Groq (Last Resort)
PROVIDERS = [
    ModelProvider.GEMINI_2_5_FLASH,
    ModelProvider.GEMINI_2_5_FLASH_LITE,
    ModelProvider.GROQ_OSS_120B
]

# Load roster and assets
LEADERSHIP_ROSTER = get_leadership_roster()
ASSETS = load_assets()

def generate_single_batch(players: List[Dict], trend_context: str, category: str, quantity: int, lore_content: str, extra_context: Dict = {}) -> List[Dict]:
    """Generates a specific batch of insights for a category"""
    logger.info(f"--- Generating Batch: {category.upper()} (Qty: {quantity}) ---")
    
    # Basic implementation for demo purposes
    # This would contain the full AI generation logic from the original file
    return [{
        "type": "info",
        "title": f"UserAccessService Migration Demo ({category})",
        "message": f"Generated {quantity} insights using UserAccessService for {len(players)} players. Trend: {trend_context[:50]}...",
        "icon": "info.png",
        "players": [p.get('username', 'Unknown') for p in players[:3]]
    }]


if __name__ == "__main__":
    """
    DEMONSTRATION: UserAccessService Migration Pattern
    
    This demonstrates how to migrate from individual database queries 
    to the unified UserAccessService approach.
    """
    try:
        # Test the new unified approach
        active_players, trend_context, extra_context = fetch_active_players(limit=10)
        
        print("=== UserAccessService Migration Demo ===")
        print(f"Active players found: {len(active_players)}")
        print(f"Trend context: {trend_context}")
        print(f"Extra context keys: {list(extra_context.keys())}")
        
        if active_players:
            print("\nSample player data (UserAccessService format):")
            sample_player = active_players[0]
            for key, value in sample_player.items():
                print(f"  {key}: {value}")
        
        # Generate sample insights
        insights = generate_single_batch(
            players=active_players,
            trend_context=trend_context, 
            category="demo",
            quantity=1,
            lore_content="",
            extra_context=extra_context
        )
        
        print(f"\nGenerated insights: {len(insights)}")
        if insights:
            print(f"Sample insight: {insights[0]}")
            
        print("\n✅ UserAccessService migration pattern demonstrated successfully!")
        
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        print(f"\n❌ Demo failed: {e}")