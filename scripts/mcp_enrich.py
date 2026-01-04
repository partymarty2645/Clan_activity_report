import sys
import os
import json
import sqlite3
import random
import time
import logging
from typing import List, Dict, Any, Optional, Tuple
import datetime
import re
import ast

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
# Pull limits from Config (defaults in Config if env missing)
ACTIVITY_WINDOW_DAYS = int(getattr(Config, "AI_ACTIVITY_DAYS", 7) or 7)
# AI_PLAYER_LIMIT now determines behavior:
#   - 0 or None: fetch ALL active players in activity window (default)
#   - > 0: fetch up to that many players (for testing/optimization)
RECENT_PLAYER_LIMIT = int(getattr(Config, "AI_PLAYER_LIMIT", 0) or 0)
ASSET_LIMIT = int(getattr(Config, "AI_ASSET_LIMIT", 300) or 300)

# Use Standardized Enum from llm_client.py
# Map provider name from config to enum
def get_provider_enum(provider_name: str):
    from services.llm_client import ModelProvider
    provider_map = {
        'gemini-2.5-flash-lite': ModelProvider.GEMINI_FLASH_LITE,
        'gemini-2.5-flash': ModelProvider.GEMINI_FLASH,
        'groq-oss-120b': ModelProvider.GROQ_OSS_120B,
    }
    return provider_map.get(provider_name, ModelProvider.GEMINI_FLASH)

LLM_PROVIDER = get_provider_enum(Config.LLM_PROVIDER)
OUTPUT_JSON_FILE = "data/ai_insights.json"
OUTPUT_JS_FILE = "docs/ai_data.js"

# --- SYSTEM PROMPT & COMMANDMENTS ---
SYSTEM_PROMPT = """You are Clank, the sarcastic clan droid. Generate brief insights for the OSRS dashboard.

RULES:
1. Accuracy: Use exact numbers from data. Never hallucinate.
2. Format: Valid JSON only. Each object: {"type":"X","message":"Y","icon":"Z"}
3. Message: 12-20 words EXACTLY. No newlines. No unescaped quotes.
4. Types: milestone, roast, trend, anomaly, leadership
5. Icons: fa-trophy, fa-skull, fa-comment, fa-chart-line, fa-crown, fa-fire, etc.
6. Unique players: Each insight targets DIFFERENT player. No repeats.
7. Tone: Casual gamer slang. No generic phrases like "keep it up" or "well done".
8. Names: Verify against roster. Use exact capitalization.

EXAMPLES:
- {"type":"milestone","message":"drylogs: 92M XP this week. Pure grind energy.","icon":"fa-trophy"}
- {"type":"roast","message":"arrogancee: 68M XP but zero messages equals bot.","icon":"fa-skull"}
- {"type":"trend","message":"sirgowi: 709 messages makes you Discord champion.","icon":"fa-comment"}

OUTPUT: Exactly 6 valid JSON objects in array format. No markdown. No explanations.
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

def get_verified_roster() -> List[str]:
    """Get all verified clan member usernames for validation."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT username FROM clan_members ORDER BY username")
        roster = [row[0] for row in cursor.fetchall()]
        conn.close()
        return roster
    except Exception as e:
        logger.warning(f"Failed to load verified roster: {e}")
        return []

def get_trend_context(cursor) -> str:
    """Get trend context information for AI generation."""
    try:
        # Get recent activity trends (Current 7d vs Prior 7d)
        cursor.execute(f"""
            SELECT COUNT(*) as msg_count
            FROM discord_messages 
            WHERE created_at >= date('now', '-7 days')
        """)
        msgs_current = cursor.fetchone()[0]

        cursor.execute(f"""
            SELECT COUNT(*) as msg_count
            FROM discord_messages 
            WHERE created_at BETWEEN date('now', '-14 days') AND date('now', '-7 days')
        """)
        msgs_prior = cursor.fetchone()[0]
        
        # Calculate Trend
        if msgs_prior > 0:
            delta_pct = ((msgs_current - msgs_prior) / msgs_prior) * 100
            trend_str = f"{delta_pct:+.1f}%"
        else:
            trend_str = "New Activity"

        trend_context = f"Discord Activity: {msgs_current} msgs this week (vs {msgs_prior} last week, Trend: {trend_str})."
        
        return trend_context
    except Exception as e:
        logger.error(f"Error getting trend context: {e}")
        return "Trend data unavailable"

def repair_json_string(json_str: str) -> str:
    """
    Aggressively repair malformed JSON from LLM output.
    Handles: unescaped quotes, newlines in strings, missing/extra brackets.
    """
    if not json_str:
        return json_str
    
    # First attempt: direct parse (might work as-is)
    try:
        return json.loads(json_str)
    except:
        pass
    
    # Pre-processing: Fix common unescaped quote issues within strings
    # Pattern: "key":"value with " in middle" -> "key":"value with \" in middle"
    # This is tricky because we need to detect quotes that aren't escaped but should be
    result = []
    in_string = False
    escape_next = False
    last_key = None
    
    for i, char in enumerate(json_str):
        # Track escape sequences
        if escape_next:
            result.append(char)
            escape_next = False
            continue
        
        if char == '\\':
            result.append(char)
            escape_next = True
            continue
        
        # Toggle string state on unescaped quotes
        if char == '"':
            in_string = not in_string
            result.append(char)
            continue
        
        # Inside a string: escape problematic characters
        if in_string:
            if char == '\n':
                result.append('\\n')
            elif char == '\r':
                result.append('\\r')
            elif char == '\t':
                result.append('\\t')
            elif char == '"':
                # This shouldn't happen (should be caught by toggle above)
                result.append('\\"')
            elif ord(char) < 32:
                # Control characters - escape them
                result.append(f'\\u{ord(char):04x}')
            else:
                result.append(char)
        else:
            # Outside strings: pass through normally
            result.append(char)
    
    repaired = ''.join(result)
    
    # Close any unclosed brackets/braces
    open_braces = repaired.count('{') - repaired.count('}')
    open_brackets = repaired.count('[') - repaired.count(']')
    
    for _ in range(open_braces):
        repaired += '}'
    for _ in range(open_brackets):
        repaired += ']'
    
    return repaired


def extract_json_array(content: str) -> Optional[List[Dict]]:
    """
    Extract JSON array from content, trying multiple strategies.
    Handles truncated responses by extracting partially complete objects.
    """
    if not content:
        return None
    
    # Strategy 1: Try direct parse
    try:
        return json.loads(content)
    except:
        pass
    
    # Strategy 2: Remove markdown wrapper (handles both ```json and ```plaintext)
    if '```' in content:
        match = re.search(r'```(?:json|plaintext|text)?\s*(.*?)\s*```', content, re.DOTALL)
        if match:
            inner = match.group(1).strip()
            try:
                return json.loads(inner)
            except:
                # If parse still fails, continue with repaired version
                content = inner
    
    # Strategy 3: Find array start and work with partial JSON
    match = re.search(r'\[', content)
    if match:
        json_candidate = content[match.start():]
        
        # Try to close incomplete arrays/objects intelligently
        # First, try basic repair with auto-closing
        try:
            repaired = repair_json_string(json_candidate)
            result = json.loads(repaired)
            if isinstance(result, list) and len(result) > 0:
                return result
        except:
            pass
        
        # Strategy 4: Extract partial objects manually
        # Look for complete objects: {..."message":"..."}
        partial_objects = []
        
        # Split on closing braces to find potential complete objects
        object_starts = [m.start() for m in re.finditer(r'\{', json_candidate)]
        
        for i, start_pos in enumerate(object_starts):
            # For each {, find a matching } that completes the object
            brace_depth = 0
            in_string = False
            escape_next = False
            
            for j in range(start_pos, len(json_candidate)):
                char = json_candidate[j]
                
                if escape_next:
                    escape_next = False
                    continue
                
                if char == '\\':
                    escape_next = True
                    continue
                
                if char == '"' and not escape_next:
                    in_string = not in_string
                    continue
                
                if not in_string:
                    if char == '{':
                        brace_depth += 1
                    elif char == '}':
                        brace_depth -= 1
                        if brace_depth == 0:
                            # Found a complete object
                            obj_str = json_candidate[start_pos:j+1]
                            try:
                                obj = json.loads(obj_str)
                                if isinstance(obj, dict) and 'message' in obj and 'type' in obj:
                                    partial_objects.append(obj)
                                    break
                            except:
                                pass
                            break
        
        if partial_objects:
            logger.info(f"Extracted {len(partial_objects)} partial objects from truncated response")
            return partial_objects
    
    return None

def extract_player_name(insight: Dict) -> Optional[str]:
    """Extract player name from insight message."""
    message = insight.get('message', '')
    words = message.split()
    if len(words) > 0:
        # First capitalized word is likely the player name
        for word in words:
            if word[0].isupper() and ':' in message[:message.index(word) + len(word) + 10]:
                return word.rstrip(':,!')
    return None

def normalize_types(insights: List[Dict], valid_types: List[str]) -> None:
    for item in insights:
        if item.get('type') not in valid_types:
            item['type'] = 'general'

def validate_insights(insights: List[Dict], verified_roster: List[str], active_players: List[Dict]) -> List[Dict]:
    """
    Post-process insights to ensure quality:
    - Remove duplicates (same player targeted)
    - Verify player names (relaxed for trends/system)
    - Filter generic phrases
    - Validate word count (very relaxed)
    - Ensure variety of types
    """
    BANNED_PHRASES = [
        "keep it up", "good job", "social butterfly", "mode activated", "well done",
        "congratulations", "amazing", "fantastic", "wonderful", "excellent",
        "absolutely love", "truly amazing", "super cool"
    ]
    
    MIN_WORDS = 5   # Relaxed from 8 to allow shorter leadership/trend messages
    MAX_WORDS = 100 
    
    filtered = []
    seen_players = set()
    active_usernames = {p['username'].lower() for p in active_players}
    verified_lower = {r.lower() for r in verified_roster}
    
    for insight in insights:
        # Extract player name (Very relaxed logic)
        message = insight.get('message', '')
        words = message.split()
        player_name = None
        insight_type = insight.get('type', 'general')
        
        # Try finding a name that exists in verified roster
        for word in words:
            clean_word = word.rstrip(':,!').lower()
            if clean_word in verified_lower:
                player_name = word.rstrip(':,!')
                break
        
        # Fallback to old extraction if valid name not found
        if not player_name and len(words) > 0:
             for word in words:
                if word[0].isupper() and ':' in message[:message.index(word) + len(word) + 10]:
                    player_name = word.rstrip(':,!')
                    break

        # Allow trend, leadership, and anomaly types without strict player name
        # Only skip if no name AND not a system-type insight
        if not player_name and insight_type not in ['trend', 'trend-positive', 'trend-negative', 'leadership', 'general', 'anomaly']:
            logger.debug(f"Could not extract player from: {insight.get('message', '')[:50]}")
            continue
        
        
        player_name_lower = player_name.lower() if player_name else None
        
        # Check for duplicate players
        if player_name_lower and player_name_lower in seen_players:
            logger.debug(f"Skipping duplicate player: {player_name}")
            continue
        
        # Verify player exists (case-insensitive) - skip for trend/system
        if player_name and player_name_lower not in verified_lower and player_name_lower not in active_usernames:
            logger.debug(f"Player name not in roster: {player_name}")
            continue
        
        # Check for banned phrases (case-insensitive)
        message = insight.get('message', '')
        message_lower = message.lower()
        has_banned = any(phrase in message_lower for phrase in BANNED_PHRASES)
        if has_banned:
            logger.debug(f"Insight contains banned phrase: {message[:60]}")
            continue
        
        # Check word count (relaxed constraints)
        word_count = len(message.split())
        if word_count < MIN_WORDS or word_count > MAX_WORDS:
            logger.debug(f"Word count {word_count} outside range [{MIN_WORDS}, {MAX_WORDS}]: {message[:50]}")
            continue
        
        # Passed all checks
        seen_players.add(player_name_lower) if player_name_lower else None
        filtered.append(insight)
    
    # Ensure type variety
    type_counts = {}
    for insight in filtered:
        itype = insight.get('type', 'general')
        type_counts[itype] = type_counts.get(itype, 0) + 1
    
    logger.info(f"Validated {len(filtered)}/{len(insights)} insights. Type distribution: {type_counts}")

    return filtered[:12]  # Cap at 12

def ensure_quality_fallback(players: List[Dict], leadership_roster: List[str]) -> List[Dict]:
    """Generate 12 diverse fallback insights from data if LLM fails."""
    fallback = []

    def _fmt(num: float) -> str:
        try:
            return f"{num:,.0f}"
        except Exception:
            return str(num)

    try:
        if not players:
            return []

        # Sort players by various metrics
        top_xp = sorted(players, key=lambda p: p.get('xp_gain', 0), reverse=True)
        top_boss = sorted(players, key=lambda p: p.get('boss_gain', 0), reverse=True)
        top_msgs = sorted(players, key=lambda p: p.get('msgs_recent', 0), reverse=True)
        activity_sorted = sorted(players, key=lambda p: p.get('activity_score', 0), reverse=True)

        used = set()
        TARGET = 12  # Always aim for 12 insights

        # === TIER 1: Hardcoded High-Value Cards (4) ===
        
        # Card 1: Top XP Grinder (milestone)
        if top_xp:
            p = top_xp[0]
            fallback.append({
                "type": "milestone", 
                "message": f"{p['username']}: {_fmt(p['xp_gain'])} XP and {_fmt(p['boss_gain'])} kills in {ACTIVITY_WINDOW_DAYS}d; pure grind energy, the clan owes you a break.", 
                "icon": "fa-trophy"
            })
            used.add(p['username'].lower())

        # Card 2: Top Boss Killer (anomaly)
        if top_boss and top_boss[0]['username'].lower() not in used:
            p = top_boss[0]
            fallback.append({
                "type": "anomaly", 
                "message": f"{p['username']}: {_fmt(p['boss_gain'])} boss kills and {_fmt(p['xp_gain'])} XP gained; loot goblin mode activated, inventory overflow imminent.", 
                "icon": "fa-skull"
            })
            used.add(p['username'].lower())

        # Card 3: Top Messenger (trend-positive)
        if top_msgs and top_msgs[0]['username'].lower() not in used:
            p = top_msgs[0]
            fallback.append({
                "type": "trend-positive", 
                "message": f"{p['username']}: {_fmt(p['msgs_recent'])} messages sent in {ACTIVITY_WINDOW_DAYS}d; the clan's vocal backbone, keep those callouts coming.", 
                "icon": "fa-comment"
            })
            used.add(p['username'].lower())

        # Card 4: Leadership (leadership)
        leader = next((p for p in top_xp if p['username'] in leadership_roster and p['username'].lower() not in used), None)
        if leader:
            fallback.append({
                "type": "leadership", 
                "message": f"{leader['username']}: Leading by example with {_fmt(leader['xp_gain'])} XP and {_fmt(leader['boss_gain'])} kills; the clan looks up to this pace.", 
                "icon": "fa-crown"
            })
            used.add(leader['username'].lower())

        # === TIER 2: Diverse Cycle Cards (8 to reach 12) ===
        # Types cycle through to ensure variety
        types_cycle = ["roast", "trend-negative", "general", "roast", "trend-negative", "general", "roast", "milestone"]
        type_idx = 0
        
        for p in activity_sorted:
            if len(fallback) >= TARGET:
                break
            if p['username'].lower() in used:
                continue
            
            # Assign type from cycle
            assigned_type = types_cycle[type_idx % len(types_cycle)]
            type_idx += 1
            
            # Generate message based on type
            if assigned_type == "roast":
                msg = f"{p['username']}: {_fmt(p['xp_gain'])} XP in {ACTIVITY_WINDOW_DAYS}d; grinding like the economy depends on it, quest point sweat confirmed."
                icon = "fa-fire"
            elif assigned_type == "trend-negative":
                msg = f"{p['username']}: {_fmt(p['boss_gain'])} boss kills this window; dry streak incoming? Stay determined, the log will return."
                icon = "fa-arrow-down"
            elif assigned_type == "milestone":
                msg = f"{p['username']}: Achieved {_fmt(p['xp_gain'])} XP and {_fmt(p['boss_gain'])} kills in {ACTIVITY_WINDOW_DAYS}d; milestone progress confirmed."
                icon = "fa-star"
            else:  # general
                msg = f"{p['username']}: Balanced contributor with {_fmt(p['xp_gain'])} XP and {_fmt(p['msgs_recent'])} messages; jack of all trades keeping the clan ecosystem thriving."
                icon = "fa-star"
            
            fallback.append({
                "type": assigned_type, 
                "message": msg, 
                "icon": icon
            })
            used.add(p['username'].lower())

        # === SAFETY: If still short, pad with final system card ===
        while len(fallback) < TARGET:
            fallback.append({
                "type": "general", 
                "message": f"Clan remains operational. {len(fallback)}/{TARGET} insights loaded.", 
                "icon": "fa-server"
            })

    except Exception as e:
        logger.error(f"Error generating fallback insights: {e}")

    # Return exactly what we have (aim for 12)
    return fallback[:TARGET] if fallback else [{"type": "general", "message": "Clan operational. Data stable.", "icon": "fa-server"}]

def fetch_active_players(limit: int = 0) -> Tuple[List[Dict], str]:
    """
    Fetch ONLY players active in the last {ACTIVITY_WINDOW_DAYS} days.
    
    Args:
        limit: Max number of players to return. If 0 (default), returns ALL active players.
    """
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 1. Get Trend Context
    trend_narrative = get_trend_context(cursor)
    
    players = []
    try:
        # Get basic member info + total stats
        cursor.execute(f"""
            SELECT m.username, m.role, m.joined_at,
                   (SELECT total_xp FROM wom_snapshots WHERE username=m.username ORDER BY timestamp DESC LIMIT 1) as total_xp,
                   (SELECT total_boss_kills FROM wom_snapshots WHERE username=m.username ORDER BY timestamp DESC LIMIT 1) as total_boss,
                   (SELECT count(*) FROM discord_messages WHERE author_name=m.username AND created_at > date('now', '-{ACTIVITY_WINDOW_DAYS} days')) as msgs_recent
            FROM clan_members m
        """)
        all_members = [dict(r) for r in cursor.fetchall()]
        
        for m in all_members:
            u = m['username']
            # Get differential for the activity window
            cursor.execute(f"""
                SELECT total_xp, total_boss_kills 
                FROM wom_snapshots WHERE username=? AND timestamp <= date('now', '-{ACTIVITY_WINDOW_DAYS} days') 
                ORDER BY timestamp DESC LIMIT 1
            """, (u,))
            base = cursor.fetchone()
            
            curr_xp = m['total_xp'] or 0
            curr_boss = m['total_boss'] or 0
            
            if base:
                xp_gain = curr_xp - (base[0] or 0)
                boss_gain = curr_boss - (base[1] or 0)
            else:
                xp_gain = curr_xp # New user or no history?
                boss_gain = curr_boss
            
            # STRICT FILTER: Must have some activity (Relaxed)
            # Was: xp < 5000 and boss_gain < 1 and msgs < 1
            # New: xp < 1000 and boss_gain < 1 and msgs < 1
            if xp_gain < 1000 and boss_gain < 1 and m['msgs_recent'] < 1:
                continue
                
            activity_score = (xp_gain / 100_000) + (boss_gain / 5) + (m['msgs_recent'] / 10)
            
            players.append({
                "username": u,
                "role": m['role'],
                "xp_gain": xp_gain,
                "boss_gain": boss_gain,
                "msgs_recent": m['msgs_recent'],
                "total_xp": curr_xp,
                "total_boss": curr_boss,
                "activity_score": activity_score
            })
            
        players.sort(key=lambda x: x['activity_score'], reverse=True)
        # If limit is 0, return all; otherwise cap at limit
        active_candidates = players if limit == 0 else players[:limit]
        
    except Exception as e:
        logger.error(f"Error fetching players: {e}")
        active_candidates = []

    conn.close()
    return active_candidates, trend_narrative

def _run_llm_single_batch(llm, players: List[Dict], leadership_roster: List[str], verified_roster: List[str], exclusions: List[str], trend_context: str, batch_label: str = "A") -> List[Dict]:
    """Request a single batch of insights (6) with optional player exclusions."""
    roster_str = ", ".join(leadership_roster)
    verified_str = ", ".join(verified_roster)
    exclusion_text = ", ".join(exclusions) if exclusions else "None"

    context_players = players[:30]
    player_context = json.dumps(context_players, indent=2)

    prompt = f"""{SYSTEM_PROMPT}

**LEADERSHIP ROSTER**: {roster_str}
**TREND CONTEXT**: {trend_context}
**TOP 30 ACTIVE PLAYERS**:
{player_context}
**EXCLUDE PLAYERS**: {exclusion_text}

**REQUIREMENT**: Return EXACTLY 6 JSON objects in valid array format. No markdown. No explanations. Do NOT use any player from EXCLUDE PLAYERS."""

    logger.info(f"Sending batch {batch_label} prompt (exclusions={len(exclusions)})...")
    response = llm.generate(prompt, temperature=Config.LLM_TEMPERATURE, max_tokens=Config.LLM_MAX_TOKENS)

    content = response.content.strip()
    try:
        with open(f"data/llm_response_raw_{batch_label}.txt", "w", encoding='utf-8') as f:
            f.write(content)
        logger.info(f"Saved raw LLM response for batch {batch_label} ({len(content)} chars)")
    except Exception as e:
        logger.warning(f"Failed to save raw response for batch {batch_label}: {e}")

    insights = extract_json_array(content) or []
    if insights:
        logger.info(f"Batch {batch_label}: extracted {len(insights)} items")
    else:
        logger.warning(f"Batch {batch_label}: no insights extracted (len={len(content)})")

    validated = validate_insights(insights, verified_roster, players)
    logger.info(f"Batch {batch_label}: validated {len(validated)} insights")
    return validated

def generate_ai_batch(players: List[Dict], trend_context: str, leadership_roster: List[str], verified_roster: List[str]) -> List[Dict]:
    """
    Generates the FULL set of insights using the 13 Commandments with enhanced prompt.
    Includes validation and deduplication.
    """
    logger.info("Initializing LLM Client...")
    
    try:
        # Initialize Client 
        llm = LLMClient(provider=LLM_PROVIDER)
        if not llm.client:
            logger.warning(f"Primary provider failed, trying fallback (Gemini Flash).")
            llm = LLMClient(provider=ModelProvider.GEMINI_FLASH)
        
        valid_types = ['milestone', 'roast', 'trend-positive', 'trend-negative', 'leadership', 'anomaly', 'general']

        batch_a = _run_llm_single_batch(llm, players, leadership_roster, verified_roster, [], trend_context, batch_label="A")
        used_names = set()
        for ins in batch_a:
            n = extract_player_name(ins)
            if n:
                used_names.add(n.lower())

        time.sleep(1.0)
        batch_b = _run_llm_single_batch(llm, players, leadership_roster, verified_roster, sorted(used_names), trend_context, batch_label="B")

        merged = []
        for ins in batch_a:
            merged.append(ins)
        for ins in batch_b:
            name = extract_player_name(ins)
            if name and name.lower() in used_names:
                continue
            merged.append(ins)
            if name:
                used_names.add(name.lower())

        normalize_types(merged, valid_types)

        TARGET = 12
        if len(merged) < TARGET:
            seen = set()
            for item in merged:
                name = extract_player_name(item)
                if name:
                    seen.add(name.lower())
            try:
                fallback_candidates = ensure_quality_fallback(players, leadership_roster)
                for card in fallback_candidates:
                    name = extract_player_name(card)
                    if name and name.lower() in seen:
                        continue
                    merged.append(card)
                    if name:
                        seen.add(name.lower())
                    if len(merged) >= TARGET:
                        break
            except Exception as e:
                logger.error(f"Structured fallback generation failed: {e}")

        merged = merged[:TARGET]

        while len(merged) < TARGET:
            merged.append({
                "type": "general", 
                "message": f"Clan reporting system active. Insight #{len(merged)+1} placeholder. Go grind!", 
                "icon": "fa-server"
            })

        logger.info(f"✅ Generated and validated {len(merged)} insights (merged two batches).")
        return merged
        
    except Exception as e:
        logger.error(f"LLM Generation Failed: {e}", exc_info=True)
        return []

def main():
    logger.info("Starting AI Analyst (Enhanced Edition)...")
    
    # 1. Fetch Data
    active_players, trend_context = fetch_active_players(limit=RECENT_PLAYER_LIMIT)
    logger.info(f"Context: {len(active_players)} active players (14d window).")
    logger.info(f"Trend: {trend_context}")
    
    # 2. Get Rosters
    leadership_roster = get_leadership_roster()
    verified_roster = get_verified_roster()
    
    # 3. Generate with validation
    insights = generate_ai_batch(active_players, trend_context, leadership_roster, verified_roster)
    
    # 4. Fallback if empty - use full 12-card fallback
    if not insights:
        logger.warning("Generating Fallback Insights (LLM failed)")
        insights = ensure_quality_fallback(active_players, leadership_roster)
        if not insights:
            # Ultimate fallback if data unavailable
            insights = [
                {"type": "anomaly", "message": "System Reboot: AI Cortex rebooting. Tracking systems operational.", "icon": "fa-server"},
                {"type": "trend-positive", "message": f"{len(active_players)} members active recently. Clan operational.", "icon": "fa-chart-line"}
            ]
    
    # 5. Save to JSON
    try:
        os.makedirs(os.path.dirname(OUTPUT_JSON_FILE), exist_ok=True)
        with open(OUTPUT_JSON_FILE, "w", encoding='utf-8') as f:
            json.dump(insights, f, indent=2)
        logger.info(f"Saved {len(insights)} insights to {OUTPUT_JSON_FILE}")
    except Exception as e:
        logger.error(f"Failed to save JSON: {e}")
        
    # 6. Save to JS
    try:
        os.makedirs(os.path.dirname(OUTPUT_JS_FILE), exist_ok=True)
        js_payload = {
            "insights": insights,
            "generated_at": datetime.datetime.now().isoformat(),
            "pulse": [i['message'] for i in insights[:5]]
        }
        with open(OUTPUT_JS_FILE, "w", encoding='utf-8') as f:
            f.write(f"window.aiData = {json.dumps(js_payload, indent=2)};")
        logger.info(f"Saved JS payload to {OUTPUT_JS_FILE}")
    except Exception as e:
        logger.error(f"Failed to save JS: {e}")

if __name__ == "__main__":
    main()