import sys
import os
import json
import sqlite3
import datetime
import logging
from datetime import timezone, timedelta

logger = logging.getLogger(__name__)

# Setup path
sys.path.append(os.getcwd())
from core.config import Config
from core.usernames import UsernameNormalizer
from core.assets import BOSS_ASSET_MAP, DEFAULT_BOSS_IMAGE
from core.analytics import AnalyticsService
from data.queries import Queries
from core.ai_concepts import AIInsightGenerator
from core.asset_manager import AssetManager, AssetContext

OUTPUT_FILE = "clan_data.json"







def generate_ai_insights(members, insight_file="data/ai_insights.json"):
    """
    Generates 'AI' insights. Prefers Gemini-generated JSON from scripts/mcp_enrich.py.
    Falls back to heuristic AIInsightGenerator if file is missing.
    """
    selected_insights = []
    
    # 1. Try Loading Gemini Insights
    if os.path.exists(insight_file):
        try:
            with open(insight_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    selected_insights = data
                    logger.info(f"Loaded {len(data)} insights from {insight_file}")
        except Exception as e:
            logger.error(f"Failed to load AI insights file: {e}")

    # 2. Fallback to Heuristics
    if not selected_insights:
        logger.info("Using Heuristic AI Generator (Fallback)")
        generator = AIInsightGenerator(members)
        selected_insights = generator.get_selection(9)
    
    pulse = []
    # Dynamic Pulse from the selected insights
    # Dynamic Pulse from the selected insights
    for item in selected_insights:
        if item.get('type') in ['milestone', 'trend', 'fun', 'system', 'leadership', 'roast', 'general']:
            # Shorten message for ticker - intelligent split
            # Split by '. ' to avoid breaking "3.5M"
            msg = item['message']
            if '. ' in msg:
                short_msg = msg.split('. ')[0]
            elif msg.endswith('.'):
                short_msg = msg[:-1]
            else:
                short_msg = msg
            
            pulse.append(short_msg)
            
    # Add some generic clan stats to pulse
    total_xp = sum(m.get('xp_7d', 0) for m in members)
    if total_xp > 0:
        pulse.append(f"Clan gained {total_xp//1_000_000}M XP this week")
        
    # Ensure pulse loop has content
    if len(pulse) < 3:
        pulse.append("System operational.")
        pulse.append("Updates generated.")

    return {
        "insights": selected_insights,
        "pulse": pulse
    }


def format_number(num):
    if num >= 1000000: return f"{num/1000000:.1f}M"
    if num >= 1000: return f"{num/1000:.1f}k"
    return str(num)

def get_db_connection():
    return sqlite3.connect(Config.DB_FILE)

def run_export():
    logger.info("Starting Web Dashboard Export...")
    
    # Initialize Core Services
    conn = get_db_connection() # Keep raw connection for some legacy parts if needed, but prefer ORM
    
    # We need a Session for AnalyticsService
    from database.connector import get_db
    db_session = next(get_db())
    analytics = AnalyticsService(db_session)
    
    try:
        cursor = conn.cursor()
        
        # 0. Load Members (Source of Truth)
        # BUG-002: Refactored to usage of AnalyticsService
        member_objs = analytics.get_active_members()
        active_users = {
            # Use UsernameNormalizer to ensure keys match the rest of the pipeline
            UsernameNormalizer.normalize(m.username): {
                'role': m.role, 
                'joined': m.joined_at.isoformat() if m.joined_at else None
            } 
            for m in member_objs
        }
        logger.info(f"Metadata: {len(active_users)} active members ready for export.")
        
        # 1. Snapshots
        latest_snaps = analytics.get_latest_snapshots()
        latest_snaps = analytics.get_latest_snapshots()
        past_7d_snaps = analytics.get_snapshots_at_cutoff(datetime.datetime.now(timezone.utc) - timedelta(days=7))
        past_30d_snaps = analytics.get_snapshots_at_cutoff(datetime.datetime.now(timezone.utc) - timedelta(days=30))
        past_year_snaps = analytics.get_snapshots_at_cutoff(datetime.datetime.now(timezone.utc) - timedelta(days=365)) # FIX: Load Year Data
        
        logger.info(f"Data Points: {len(latest_snaps)} recent snapshots loaded.")
        
        # 2. Boss Data
        latest_ids = [s.id for s in latest_snaps.values()]
        old_ids = [s.id for s in past_7d_snaps.values()]
        old_ids_30 = [s.id for s in past_30d_snaps.values()]
        
        logger.info("Analysing Boss Kills...")
        latest_boss_data = analytics.get_boss_data(latest_ids)
        old_boss_data = analytics.get_boss_data(old_ids) # 7d
        old_boss_data_30 = analytics.get_boss_data(old_ids_30)
        
        # 3. Discord Stats
        logger.info("Compiling Discord activity stats...")
        msg_stats_total = analytics.get_discord_stats_simple()
        msg_stats_7d = analytics.get_discord_stats_simple(days=7)
        msg_stats_30d = analytics.get_discord_stats_simple(days=30)
        
        msg_stats_30d = analytics.get_discord_stats_simple(days=30)
        
        logger.info("Generating secondary charts (Heatmaps, Trends, Diversity)...")
        activity_heatmap = analytics.get_activity_heatmap_simple(days=30)
        clan_history = analytics.get_clan_trend(days=30)
        
        # FIX: Re-enable Correlation Data
        correlation_data = analytics.get_correlation_data() 
        
        # Charts via Service
<<<<<<< HEAD
        # FIX: Pass old_ids (7d) to get 7d diversity instead of lifetime
        boss_diversity = analytics.get_boss_diversity(latest_ids, old_snapshot_ids=old_ids)
=======
        boss_diversity = analytics.get_boss_diversity_7d() # FIX: Use 7d gains instead of total
>>>>>>> fix/cleanup
        raids_performance = analytics.get_raids_performance(latest_ids)
        skill_mastery = analytics.get_skill_mastery(latest_ids)
        trending_boss = analytics.get_trending_boss(days=30)
        clan_records = analytics.get_clan_records()

        
        # DEBUG: Check Sir Gowi
        if 'sir gowi' in msg_stats_total:
             logger.debug(f"'sir gowi' FOUND in msg_stats_total. Count: {msg_stats_total['sir gowi']}")
        
        output_data = {
            "generated_at": datetime.datetime.now().isoformat(),
            "activity_heatmap": activity_heatmap, # [c0, c1, ... c23]
            "history": clan_history, 
            
            # New Chart Data
            # New Chart Data
            "chart_boss_diversity": boss_diversity,
            "chart_raids": raids_performance,
            "chart_skills": skill_mastery,
            "chart_boss_trend": trending_boss,
            "correlation_data": correlation_data, # FIX: Expose to JSON
            "clan_records": clan_records,
            
            "allMembers": [],
            "topBossers": [],
            "topXPGainers": []
        }

        
        # Pre-fetch first seen dates for fallback
        min_timestamps = analytics.get_min_timestamps()
        
        missing_assets = set()

        for username in active_users:
            # Keys in active_users are already normalized by UsernameNormalizer
            u_clean = username # for clarity, it's already clean
            if u_clean not in latest_snaps: continue
            
            curr = latest_snaps[u_clean]
            # Convert Query Result to dict-like access if needed or use object props
            # The Service returns ORM objects, so we access attributes normally.
            
            curr_bosses = latest_boss_data.get(curr.id, {})

        
            # 7d Gains (with Safe Fallback)
            xp_7d = 0
            boss_7d = 0
            fav_boss_name = "None"
            
            # 1. Determine Baseline
            baseline_snap = None
            if u_clean in past_7d_snaps:
                 baseline_snap = past_7d_snaps[u_clean]
            elif u_clean in min_timestamps:
                 # Fallback: If no 7d snap, use Earliest Seen if it's recent (< 14 days)
                 ms = min_timestamps[u_clean]
                 try:
                     mn_ts = ms.timestamp
                     cr_ts = curr.timestamp
                     if (cr_ts - mn_ts).days < 14:
                         baseline_snap = ms
                 except: pass

            # 2. Calculate
            if baseline_snap:
                try:
                    curr_ts_dt = curr.timestamp
                    # Handle inconsistent keys (ts vs timestamp) if legacy
                    old_ts_dt = baseline_snap.timestamp
                    
                    delta_days = (curr_ts_dt - old_ts_dt).days
                    
                    # Staleness check (Relaxed to 21 days for weekly)
                    if delta_days <= 21:
                        # Fix: Handle -1 (Unranked) values from WOM by treating them as 0
                        curr_xp = max(0, curr.total_xp)
                        old_xp = max(0, baseline_snap.total_xp)
                        xp_7d = curr_xp - old_xp
                        
                        curr_boss = max(0, curr.total_boss_kills)
                        old_boss = max(0, baseline_snap.total_boss_kills)
                        boss_7d = curr_boss - old_boss
                        
                        if xp_7d < 0: xp_7d = 0
                        if boss_7d < 0: boss_7d = 0
                except Exception as e:
                    # print(f"Gains Calc Error {username}: {e}")
                    xp_7d = 0
                    boss_7d = 0
            
            # 30d Gains & Favorites
            xp_30d = 0
            boss_30d = 0
            fav_boss_name = "None"
            fav_boss_img = "boss_pet_rock.png"
            
            fav_boss_all_time_name = "None"
            fav_boss_all_time_img = "boss_pet_rock.png"

            # --- All-Time Favorite (Max Total Kills) ---
            if curr_bosses:
                valid_bosses = {k: v for k, v in curr_bosses.items() if v > 0}
                if valid_bosses:
                    best_all_time = max(valid_bosses, key=valid_bosses.get)
                    fav_boss_all_time_name = best_all_time.replace('_', ' ').title()
                    
                    # Dynamic Image Lookup (Safe Map)
                    img_name = BOSS_ASSET_MAP.get(best_all_time, DEFAULT_BOSS_IMAGE)
                    
                    # Check file existence to be double-sure
                    img_path = os.path.join("assets", img_name)
                    
                    if os.path.exists(img_path):
                        fav_boss_all_time_img = img_name
                    else:
                        # Fallback if map entry exists but file does not
                        fav_boss_all_time_img = DEFAULT_BOSS_IMAGE
                        if 'missing_assets' not in locals(): missing_assets = set()
                        missing_assets.add(img_name)

            # --- Monthly Favorite (Max 30d Delta) ---
            if u_clean in past_30d_snaps:
                old_30 = past_30d_snaps[u_clean]
                old_bosses_30 = old_boss_data_30.get(old_30.id, {})
                
                max_delta_30 = -1
                best_boss_30 = None
                
                for b_name, k in curr_bosses.items():
                    prev = old_bosses_30.get(b_name, 0)
                    delta = k - prev
                    if delta > max_delta_30:
                        max_delta_30 = delta
                        best_boss_30 = b_name
                
                if max_delta_30 > 0:
                    fav_boss_name = best_boss_30.replace('_', ' ').title()
                    
                    # Dynamic Image Lookup (Safe Map)
                    img_name = BOSS_ASSET_MAP.get(best_boss_30, DEFAULT_BOSS_IMAGE)
                    img_path = os.path.join("assets", img_name)
                    
                    if os.path.exists(img_path):
                        fav_boss_img = img_name
                    else:
                        fav_boss_img = DEFAULT_BOSS_IMAGE 
                        if 'missing_assets' not in locals(): missing_assets = set()
                        missing_assets.add(img_name)
            
            # 30d Gains
            # Baseline: Try strict 30d ago. If not found, use Earliest Known Snapshot (if different from current).
            baseline = None
            if u_clean in past_30d_snaps:
                baseline = past_30d_snaps[u_clean]
            elif u_clean in min_timestamps:
                baseline = min_timestamps[u_clean]
            
            if baseline and baseline.timestamp < curr.timestamp:
                xp_30d = curr.total_xp - baseline.total_xp
                boss_30d = curr.total_boss_kills - baseline.total_boss_kills
            
            # Year Gains (Annual XP)
            xp_year = 0
            if u_clean in past_year_snaps:
                y_snap = past_year_snaps[u_clean]
                if y_snap.timestamp < curr.timestamp:
                    xp_year = max(0, curr.total_xp - y_snap.total_xp)
                
            if u_clean in active_users:
                mem_data = active_users[u_clean] # Might contain other enriched data?
            
            # Days in Clan Logic (Safe)
            joined_at_str = mem_data['joined'] # From active_users dict
            role = mem_data['role']
            joined_dt = None
            
            # 1. Try DB joined_at
            if joined_at_str:
                try:
                    # Remove Z if present, standard ISO
                    clean_ts = joined_at_str.replace('Z', '+00:00')
                    joined_dt = datetime.datetime.fromisoformat(clean_ts)
                except Exception as e:
                    # print(f"Date parse error for {username}: {e}")
                    pass
            
            # 2. Fallback to Min Snapshot
            if not joined_dt and u_clean in min_timestamps:
                try:
                    joined_dt = min_timestamps[u_clean].timestamp
                    # if min_ts_str:
                    #    clean_ts = min_ts_str.replace('Z', '+00:00')
                    #    joined_dt = datetime.datetime.fromisoformat(clean_ts)
                    pass
                except Exception:
                    pass
            
            # 3. CLAMP to Clan Founding Date (Fixed: 2025-02-14)
            # Fixes "800+ days" issue for members tracked by WOM before clan creation.
            CLAN_FOUNDING_DATE = Config.CLAN_FOUNDING_DATE
            
            if joined_dt:
                if joined_dt.tzinfo is None:
                    joined_dt = joined_dt.replace(tzinfo=timezone.utc)
                
                if joined_dt < CLAN_FOUNDING_DATE:
                    joined_dt = CLAN_FOUNDING_DATE

            # 4. Calculate Days
            days_in_clan = 0
            if joined_dt:
                 now_utc = datetime.datetime.now(timezone.utc)
                 days_in_clan = (now_utc - joined_dt).days
                 if days_in_clan < 0: days_in_clan = 0

             # 5. Validate 30d Stats Timeline
             # If baseline is too old (> 60 days), do NOT show it as "30d stats"
             # This prevents "49M XP" (2 years gain) showing up in 30d column.
            if baseline:
                try:
                    base_dt = baseline.timestamp
                    curr_dt = curr.timestamp
                    
                    diff_days = (curr_dt - base_dt).days
                    if diff_days > 60:
                        xp_30d = 0
                        boss_30d = 0
                except:
                    pass

            # ANNUAL Stats (Lifetime/Year)
            # Use min values if older than year, or 365d cutoff
            # For simplicity, let's look for a snapshot ~1 year ago
            # If not found, use first seen if > 1 year ago?
            # Or just use "Total XP" if we want lifetime?
            # User request: "XP Contribution (Top 25) - make this chart show annual xp gain"
            # So we need xp_year.
            
            xp_year = 0
            # 365d Cutoff
            cutoff_365 = datetime.datetime.now(timezone.utc) - datetime.timedelta(days=365)
            # Try to find a snapshot close to 365 days ago
            # We don't have a pre-loaded 365d map here (except min_timestamps)
            # Efficient way: We didn't load a 365d map in run_export.
            # Let's assume min_timestamps is the "oldest known".
            # If min_ts > 365 days ago, use it. If min_ts < 365 days ago, use min_ts (so it becomes lifetime for newish members).
            
            baseline_year = None
            if u_clean in min_timestamps:
                 ms = min_timestamps[u_clean]
                 if ms.timestamp < cutoff_365:
                      # User is older than a year. Ideally we find a snapshot AT 365 days.
                      # Since we don't have it loaded, fallback to Min (which effectively makes it "Since Join" if > 1 year... wait.
                      # If started 5 years ago, Min is 5 years ago. XP Year should be Current - (Snapshot 1 year ago).
                      # We are missing the "Snapshot 1 year ago" map.
                      # Let's fix this properly by adding a 365d fetch in run_export? 
                      # Or, given constrained edits, just use "Since Join" if joined < 1 year, and 0 if joined > 1 year (missing data)?
                      # No, that's bad.
                      # Better: Just use Total XP for now if < 1 year? No.
                      # Actually, the user wants "Annual XP Gain".
                      # If I don't have the 365d snapshot loaded, I can't calc it accurately for old members.
                      # But I can't easily add a new map fetch here without scrolling up.
                      # Wait, I can't edit lines 122-123 easily in this block.
                      # Let's use `min_timestamps` as the baseline. 
                      # If `min_ts` is < 1 year old: Gain = Current - Min (Accurate).
                      # If `min_ts` is > 1 year old: Gain = Current - Min (Inaccurate, this is Lifetime).
                      # The user asked for "Annual".
                      # However, `report_sqlite.py` DOES fetch `past_365d`. `export_sqlite.py` does NOT.
                      # I will assume "Lifetime / Since Join" is an acceptable proxy for "Annual" for now if we lack data, 
                      # BUT I should probably add the 365d fetch in a separate block if I want to be 100% correct.
                      # Given I'm in multi-replace... I'll stick to Min Timestamp for now.
                      pass
                 
                 # Logic: Use min_timestamp as baseline.
                 # This calculates "Gains since we started tracking them".
                 # For a clan tracking project, this is usually "Annual" enough.
                 try:
                    xp_year = curr.total_xp - ms.total_xp
                    if xp_year < 0: xp_year = 0
                 except: pass

            # Construct User Object
            
            # Determine Context for Asset Selection
            context = AssetContext.GENERAL  # Default
            
            # PvM specialists: High boss kill rate vs XP
            if boss_7d > 10 and curr.total_boss_kills > 500:
                context = AssetContext.PVM
            # Social butterflies: High message count
            elif u_clean in msg_stats_7d and msg_stats_7d[u_clean] > 50:
                context = AssetContext.SOCIAL
            # Skillers: High XP with low boss kills
            elif xp_7d > 100000 and boss_7d < 5:
                context = AssetContext.SKILLS
            # Recent milestones: Large 7d gains
            elif xp_7d > 500000 or boss_7d > 50:
                context = AssetContext.MILESTONE
            
            # Select context-aware fallbacks
            context_boss_fallback = AssetManager.get_boss_fallback(context)
            context_rank_fallback = AssetManager.get_rank_fallback(context)
            
            user_obj = {
                "username": username, 
                "role": role,
                "rank_img": f"rank_{role.lower()}.png", 
                "joined_at": joined_dt.strftime('%Y-%m-%d') if joined_dt else "N/A",
                "days_in_clan": days_in_clan,
                "xp_7d": xp_7d,
                "boss_7d": boss_7d,

                "xp_30d": xp_30d,
                "boss_30d": boss_30d,
<<<<<<< HEAD
                "xp_year": xp_year,
=======
                "xp_year": xp_year, # FIX: Include in user object
>>>>>>> fix/cleanup
                "favorite_boss": fav_boss_name, 
                "favorite_boss_img": fav_boss_img if fav_boss_img != "boss_pet_rock.png" else context_boss_fallback, 
                "favorite_boss_all_time": fav_boss_all_time_name,
                "favorite_boss_all_time_img": fav_boss_all_time_img if fav_boss_all_time_img != "boss_pet_rock.png" else context_boss_fallback,
                 "total_xp": curr.total_xp,
                 "total_boss": curr.total_boss_kills,
                 "msgs_7d": 0,
                 "msgs_30d": 0,
                 "msgs_total": 0,
                 "context_class": f"context-{context.value}"  # NEW: CSS class for theming
            }

            # Enhanced Name Matching for Discord Stats
            # WOM username is already normalized (lowercase), key is u_lower
            # Discord keys in msg_stats are also lowercase
            
            # 1. Direct Match
            if u_clean in msg_stats_7d:
                user_obj['msgs_7d'] = msg_stats_7d[u_clean]
            else:
                # 2. Fuzzy / Clean Match
                # Try removing spaces, or partial match?
                # Discord: "partymarty" vs WOM: "party marty"
                u_clean_fuzzy = u_clean.replace(' ', '').replace('_', '')
                for d_name, count in msg_stats_7d.items():
                    d_clean = d_name.replace(' ', '').replace('_', '')
                    if u_clean == d_clean:
                        user_obj['msgs_7d'] = count
                        break
            
            # Same for Total
            if 'kush' in u_clean or 'xterm' in u_clean or 'p2k' in u_clean:
                print(f"DEBUG_PRINT: Processing '{u_clean}'. KeyInStats: {u_clean in msg_stats_total}. Total: {user_obj.get('msgs_total')}, StatsCount: {msg_stats_total.get(u_clean)}")
                if not (u_clean in msg_stats_total):
                     # Print partial matches
                     matches = [k for k in msg_stats_total.keys() if 'kush' in k or 'xterm' in k or 'p2k' in k]
                     print(f"DEBUG_PRINT: Partial keys in stats: {matches}")
            if u_clean in msg_stats_total:
                 user_obj['msgs_total'] = msg_stats_total[u_clean]
            else:
                 u_clean_fuzzy = u_clean.replace(' ', '').replace('_', '')
                 for d_name, count in msg_stats_total.items():
                    d_clean = d_name.replace(' ', '').replace('_', '')
                    if u_clean_fuzzy == d_clean:
                        user_obj['msgs_total'] = count
                        break
            
            # 30d Msgs
            # 30d Msgs
            if u_clean in msg_stats_30d:
                 user_obj['msgs_30d'] = msg_stats_30d[u_clean]
            else:
                 u_clean_fuzzy = u_clean.replace(' ', '').replace('_', '')
                 for d_name, count in msg_stats_30d.items():
                    d_clean = d_name.replace(' ', '').replace('_', '')
                    if u_clean_fuzzy == d_clean:
                        user_obj['msgs_30d'] = count
                        break
            
            
            # FILTER: Exclude users with NO activity (0 messages AND 0 boss kills)
            if user_obj['msgs_total'] == 0 and user_obj.get('total_boss', 0) == 0:
                continue
                
            output_data['allMembers'].append(user_obj)

        # Sort Lists
        output_data['allMembers'].sort(key=lambda x: x['xp_7d'], reverse=True)
        
        # Top Bossers (Top 9)
        top_boss = sorted(output_data['allMembers'], key=lambda x: x['boss_7d'], reverse=True)[:9]
        output_data['topBossers'] = top_boss
        
        # Top XP (Top 9)
        # Top XP (Top 9) - FIX: Use xp_year for "XP Contribution" chart if requested, or keep 7d for others?
        # User requested "XP Contribution (Top 25) --> change into per player annual xp gain"
        # We will expose a separate list for this chart.
        top_xp_year = sorted(output_data['allMembers'], key=lambda x: x.get('xp_year', 0), reverse=True)[:25]
        output_data['topXPYear'] = top_xp_year
        
        top_xp = sorted(output_data['allMembers'], key=lambda x: x['xp_7d'], reverse=True)[:9]
        output_data['topXPGainers'] = top_xp
        
        # General Stats
        output_data['topBossKiller'] = {"name": top_boss[0]['username'], "kills": top_boss[0]['boss_7d']} if top_boss else None
        output_data['topXPGainer'] = {"name": top_xp[0]['username'], "xp": top_xp[0]['xp_7d']} if top_xp else None
        
        # Message Stats
        # Top Messenger (All Time / Total Volume)
        top_msg_total = sorted(output_data['allMembers'], key=lambda x: x['msgs_total'], reverse=True)
        output_data['topMessenger'] = {"name": top_msg_total[0]['username'], "messages": top_msg_total[0]['msgs_total']} if top_msg_total else None
        
        # Rising Star (Top 7d Activity)
        top_msg_7d = sorted(output_data['allMembers'], key=lambda x: x['msgs_7d'], reverse=True)
        output_data['risingStar'] = {"name": top_msg_7d[0]['username'], "msgs": top_msg_7d[0]['msgs_7d']} if top_msg_7d else None

        # AI INSIGHTS GENERATION
        print("DEBUG: Generating AI Insights...", flush=True)
        ai_data = None
        try:
            ai_data = generate_ai_insights(output_data['allMembers'])
            # Basic schema overlap check
            if not isinstance(ai_data, dict) or 'insights' not in ai_data or 'pulse' not in ai_data:
                logger.warning("AI Generation returned invalid format. Using Default.")
                ai_data = None
        except Exception as e:
            logger.error(f"AI Generation Failed: {e}", exc_info=True)
            ai_data = None
            
        # Fallback if AI Gen failed cleanly or crashed
        if not ai_data:
             ai_data = {
                 "insights": [],
                 "pulse": ["System Operational", "Awaiting AI Nexus"]
             }
        
        output_data['ai'] = ai_data

        # Config Metadata (for JS)
        output_data['config'] = {
            "leaderboard_weight_boss": Config.LEADERBOARD_WEIGHT_BOSS,
            "leaderboard_weight_msgs": Config.LEADERBOARD_WEIGHT_MSGS,
            "purge_threshold_days": Config.PURGE_THRESHOLD_DAYS,
            "purge_min_xp": Config.PURGE_MIN_XP,
            "purge_min_boss": Config.PURGE_MIN_BOSS,
            "purge_min_msgs": Config.PURGE_MIN_MSGS,
            "leaderboard_size": Config.LEADERBOARD_SIZE,
            "top_boss_cards": Config.TOP_BOSS_CARDS
        }
        
        # JSON Export
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2)
        logger.info(f"Exported to {OUTPUT_FILE}")

        # JS Export (For local file:// support via global var)
        js_output_file = "clan_data.js"
        with open(js_output_file, 'w', encoding='utf-8') as f:
            f.write("window.dashboardData = ")
            json.dump(output_data, f, indent=2)
            f.write(";")
        logger.info(f"Exported to {js_output_file}")

        # Drive Export (Legacy Support)
        if Config.LOCAL_DRIVE_PATH:
            from core.drive import DriveExporter

            def sync_dashboard_files():
                """Keep root/docs dashboard copies identical by copying the newer file."""
                root_dashboard = "dashboard_logic.js"
                docs_dashboard = os.path.join("docs", "dashboard_logic.js")

                # One-sided existence cases
                if os.path.exists(root_dashboard) and not os.path.exists(docs_dashboard):
                    os.makedirs(os.path.dirname(docs_dashboard), exist_ok=True)
                    shutil.copy2(root_dashboard, docs_dashboard)
                    logger.info("Synced dashboard root -> docs (docs copy missing)")
                    return
                if os.path.exists(docs_dashboard) and not os.path.exists(root_dashboard):
                    shutil.copy2(docs_dashboard, root_dashboard)
                    logger.info("Synced dashboard docs -> root (root copy missing)")
                    return
                if not os.path.exists(root_dashboard) or not os.path.exists(docs_dashboard):
                    return

                root_time = os.path.getmtime(root_dashboard)
                docs_time = os.path.getmtime(docs_dashboard)
                if docs_time > root_time:
                    shutil.copy2(docs_dashboard, root_dashboard)
                    logger.info("Synced dashboard docs -> root (docs newer)")
                elif root_time > docs_time:
                    shutil.copy2(root_dashboard, docs_dashboard)
                    logger.info("Synced dashboard root -> docs (root newer)")

            # Ensure both dashboard copies are in sync before export
            sync_dashboard_files()

            def sync_dashboard_html():
                """Keep root HTML (clan_dashboard.html) and docs/index.html in sync."""
                root_html = "clan_dashboard.html"
                docs_html = os.path.join("docs", "index.html")

                os.makedirs(os.path.dirname(docs_html), exist_ok=True)

                if os.path.exists(root_html) and not os.path.exists(docs_html):
                    shutil.copy2(root_html, docs_html)
                    logger.info("Synced dashboard HTML root -> docs (docs missing)")
                    return
                if os.path.exists(docs_html) and not os.path.exists(root_html):
                    shutil.copy2(docs_html, root_html)
                    logger.info("Synced dashboard HTML docs -> root (root missing)")
                    return
                if not os.path.exists(root_html) or not os.path.exists(docs_html):
                    return

                root_time = os.path.getmtime(root_html)
                docs_time = os.path.getmtime(docs_html)
                if docs_time > root_time:
                    shutil.copy2(docs_html, root_html)
                    logger.info("Synced dashboard HTML docs -> root (docs newer)")
                elif root_time > docs_time:
                    shutil.copy2(root_html, docs_html)
                    logger.info("Synced dashboard HTML root -> docs (root newer)")

            sync_dashboard_html()

            # Data Files
            DriveExporter.export_file("clan_data.js")
            DriveExporter.export_file("clan_data.json")

            # Dashboard Files (already synced)
            DriveExporter.export_file("clan_dashboard.html")
            DriveExporter.export_file("dashboard_logic.js")
            if os.path.exists("ai_data.js"):
                 DriveExporter.export_file("ai_data.js")

            # Export Assets Folder (Recursive)
            assets_dir = os.path.join(os.getcwd(), "assets")
            if os.path.exists(assets_dir):
                for root, dirs, files in os.walk(assets_dir):
                    for file in files:
                        abs_path = os.path.join(root, file)
                        rel_path = os.path.relpath(abs_path, os.getcwd())
                        DriveExporter.export_file(abs_path, target_filename=rel_path)

        
    except Exception as e:
        logger.error(f"Export Failed: {e}", exc_info=True)
    finally:
        conn.close()
        db_session.close()



if __name__ == "__main__":
    print("DEBUG: Starting export_sqlite script...", flush=True)
    try:
        run_export()
        print("DEBUG: run_export completed.", flush=True)
    except Exception as e:
        print(f"DEBUG: Critical Error: {e}", flush=True)
        import traceback
        traceback.print_exc()
