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

DB_PATH = "clan_data.db"
OUTPUT_FILE = "clan_data.json"







def generate_ai_insights(members):
    """
    Generates procedural 'AI' insights using the expanded random pool.
    Returns a dict with 'insights' (list of cards) and 'pulse' (list of ticker strings).
    """
    # Initialize Generator
    generator = AIInsightGenerator(members)
    
    # Get 9 random insights
    selected_insights = generator.get_selection(9)
    
    # Generate Pulse separately or extract from insights?
    # For now, let's keep pulse simple or generate it:
    
    pulse = []
    # Dynamic Pulse from the selected insights
    for item in selected_insights:
        if item['type'] in ['milestone', 'trend', 'fun', 'system']:
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
    return sqlite3.connect(DB_PATH)

def get_latest_snapshots(cursor):
    # Get latest snapshot for each user
    cursor.execute(Queries.GET_LATEST_SNAPSHOTS)
    rows = cursor.fetchall()
    return {r[1]: {'id': r[0], 'ts': r[2], 'xp': r[3], 'boss': r[4]} for r in rows}

    return {r[1]: {'id': r[0], 'ts': r[2], 'xp': r[3], 'boss': r[4]} for r in rows}

def get_min_timestamps(cursor):
    # Get the FIRST seen snapshot for each user (timestamp + data)
    cursor.execute(Queries.GET_MIN_TIMESTAMPS)
    # Return dict: username -> {ts, xp, boss}
    return {r[0]: {'ts': r[1], 'xp': r[2], 'boss': r[3]} for r in cursor.fetchall()}

def get_past_snapshots(cursor, cutoff_days=7):
    # For each user, find the snapshot that is closest to 'cutoff_days' ago
    
    target_date = datetime.datetime.now(timezone.utc) - timedelta(days=cutoff_days)
    target_iso = target_date.isoformat()
    
    cursor.execute(Queries.GET_SNAPSHOTS_AT_CUTOFF, (target_iso,))
    
    rows = cursor.fetchall()
    return {r[1]: {'id': r[0], 'ts': r[2], 'xp': r[3], 'boss': r[4]} for r in rows}

def get_boss_data(cursor, snapshot_ids):
    if not snapshot_ids: return {}
    # sqlite limit variables is usually 999. We might need to chunk.
    ids = list(snapshot_ids)
    result = {}
    
    chunk_size = 500
    for i in range(0, len(ids), chunk_size):
        chunk = ids[i:i+chunk_size]
        placeholders = ','.join('?' * len(chunk))
        cursor.execute(Queries.GET_BOSS_DATA_CHUNK.format(placeholders), chunk)
        
        for row in cursor.fetchall():
            sid, name, kills = row
            if sid not in result: result[sid] = {}
            result[sid][name] = kills
            
    return result

def get_clan_trend(cursor, days=30):
    # Aggregate Clan-Wide XP and Messages per day
    # We need 1 extra day of history to calculate the first day's gain
    start_date = datetime.datetime.now(timezone.utc) - timedelta(days=days+1)
    cutoff_ts = start_date.isoformat()
    
    trend_data = {} # date_str -> {'xp_total': 0, 'msgs': 0, 'xp_gain': 0}

    # 1. Calculate Daily Clan XP Total (Sum of max xp per user per day)
    try:
        cursor.execute(Queries.GET_DAILY_XP_MAX, (cutoff_ts,))
        
        # Aggregate to daily total
        daily_totals = {} # day -> sum_xp
        for row in cursor.fetchall():
            day, user, xp = row
            if day not in daily_totals: daily_totals[day] = 0
            daily_totals[day] += xp
            
        # Calculate Gains (Day N - Day N-1)
        sorted_days = sorted(daily_totals.keys())
        for i in range(1, len(sorted_days)):
            curr_day = sorted_days[i]
            prev_day = sorted_days[i-1]
            gain = daily_totals[curr_day] - daily_totals[prev_day]
            # Verify gain is positive (re-names or resets can cause negative dips, ignore those)
            if gain < 0: gain = 0 
            
            if curr_day not in trend_data: trend_data[curr_day] = {'msgs': 0, 'xp_gain': 0}
            trend_data[curr_day]['xp_gain'] = gain

    except sqlite3.OperationalError as e:
        print(f"Warning: XP Trend calculation failed: {e}")

    # 2. Daily Messages Sum
    try:
        cursor.execute(Queries.GET_DAILY_MSGS, (cutoff_ts,))
        
        for row in cursor.fetchall():
            day, count = row
            if day not in trend_data: trend_data[day] = {'msgs': 0, 'xp_gain': 0}
            trend_data[day]['msgs'] = count
            
    except sqlite3.OperationalError as e:
        print(f"Warning: Message Trend calculation failed: {e}")

    # Convert to sorted list for the last 'days' (exclude the buffer day if used only for diff)
    result = []
    display_start = datetime.datetime.now(timezone.utc) - timedelta(days=days)
    
    for i in range(days):
        d = (display_start + timedelta(days=i)).strftime('%Y-%m-%d')
        # If no data for this day, defaults to 0
        val = trend_data.get(d, {'msgs': 0, 'xp_gain': 0})
        result.append({'date': d, 'xp': val['xp_gain'], 'msgs': val['msgs']})
        
    return result

# --- NEW AGGREGATIONS FOR CHARTS ---

def get_boss_diversity(cursor, snapshot_ids):
    # Sum of all kills per boss for the latest snapshot
    if not snapshot_ids: return {}
    ids = list(snapshot_ids)
    
    placeholders = ','.join('?' * len(ids))
    cursor.execute(Queries.GET_BOSS_DIVERSITY.format(placeholders), ids)
    
    data = cursor.fetchall() # list of (name, count)
    
    # Process for Chart: All Bosses (User Request)
    labels = []
    values = []
    
    # Sort by count desc
    data.sort(key=lambda x: x[1], reverse=True)
    
    for row in data:
        if row[1] > 0:
            labels.append(row[0].replace('_', ' ').title())
            values.append(row[1])
            
    return {"labels": labels, "datasets": [{"data": values}]}

def get_raids_performance(cursor, snapshot_ids):
    if not snapshot_ids: return {}
    ids = list(snapshot_ids)
    placeholders = ','.join('?' * len(ids))
    
    # Explicitly check for raids
    raids_map = {
        'Chambers Of Xeric': 'CoX',
        'Chambers Of Xeric Challenge Mode': 'CoX',
        'Theatre Of Blood': 'ToB',
        'Theatre Of Blood Hard Mode': 'ToB',
        'Tombs Of Amascut': 'ToA',
        'Tombs Of Amascut Expert': 'ToA'
    }
    
    raids_counts = {'CoX': 0, 'ToB': 0, 'ToA': 0}
    
    cursor.execute(Queries.GET_BOSS_SUMS_FOR_IDS.format(placeholders), ids)
    
    for row in cursor.fetchall():
        name = row[0].replace('_', ' ').title()
        if name in raids_map:
            short_name = raids_map[name]
            raids_counts[short_name] += row[1]
            
    # Return keys and values for chart
    return {
        "labels": list(raids_counts.keys()),
        "datasets": [{"data": list(raids_counts.values())}]
    }

def get_skill_mastery(cursor, snapshot_ids):
    # Count how many people have 99 in each skill using raw_data JSON
    if not snapshot_ids: return {}
    ids = list(snapshot_ids)
    placeholders = ','.join('?' * len(ids))
    
    try:
        cursor.execute(Queries.GET_RAW_DATA_FOR_IDS.format(placeholders), ids)
    except sqlite3.OperationalError:
        print("Warning: 'raw_data' column likely missing in wom_snapshots. Skipping Skill Mastery.")
        return {}
    
    skill_counts = {}
    
    for row in cursor.fetchall():
        if not row[0]: continue
        try:
            data = json.loads(row[0])
            # WOM structure: data -> data -> skills 
            skills = data.get('data', {}).get('skills', {})
            if not skills:
                skills = data.get('skills', {})
                
            for skill_name, stats in skills.items():
                if skill_name == 'overall': continue
                if stats.get('level', 0) >= 99:
                    skill_counts[skill_name] = skill_counts.get(skill_name, 0) + 1
                    
        except json.JSONDecodeError:
            continue
            
    sorted_skills = sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)
    
    labels = [s[0].title() for s in sorted_skills]
    values = [s[1] for s in sorted_skills]
        
    return {"labels": labels, "datasets": [{"data": values}]}

def get_trending_boss_monthly(cursor, days=30):
    # Identify the boss with the highest DELTA in total clan kills over last 30 days

    latest_snaps = get_latest_snapshots(cursor)
    past_30_snaps = get_past_snapshots(cursor, days)
    
    if not latest_snaps: return None
    
    latest_ids = [v['id'] for v in latest_snaps.values()]
    past_ids = [v['id'] for v in past_30_snaps.values()]
    
    # Helper to sum
    def sum_bosses(sids):
        if not sids: return {}
        ph = ','.join('?' * len(sids))
        cursor.execute(Queries.GET_BOSS_SUMS_FOR_IDS.format(ph), list(sids))
        return {row[0]: row[1] for row in cursor.fetchall()}

    now_sums = sum_bosses(latest_ids)
    old_sums = sum_bosses(past_ids)
    
    deltas = {}
    for boss, kills in now_sums.items():
        prev = old_sums.get(boss, 0)
        gain = kills - prev
        if gain > 0:
            deltas[boss] = gain
            
    if not deltas: return None
    
    top_boss = max(deltas, key=deltas.get) 
    
    # Now get DAILY data for this boss for the chart
    cutoff_dt = datetime.datetime.now(timezone.utc) - timedelta(days=days)
    
    cursor.execute(Queries.GET_DAILY_BOSS_KILLS, (cutoff_dt.isoformat(), top_boss))
    
    daily_raw = {row[0]: row[1] for row in cursor.fetchall()}
    
    if not daily_raw:
        today_str = datetime.datetime.now(timezone.utc).strftime('%Y-%m-%d')
        daily_raw = {today_str: now_sums.get(top_boss, 0)}
    
    sorted_days = sorted(daily_raw.keys())
    
    labels = []
    values = []
    
    for i in range(1, len(sorted_days)):
        d_curr = sorted_days[i]
        d_prev = sorted_days[i-1]
        gain = daily_raw[d_curr] - daily_raw[d_prev]
        if gain < 0: gain = 0
        labels.append(d_curr)
        values.append(gain)
        
    return {
        "boss_name": top_boss.replace('_', ' ').title(), 
        "total_gain": deltas[top_boss],
        "chart_data": {"labels": labels, "datasets": [{"data": values, "label": "Daily Kills"}]}
    }



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
        past_7d_snaps = analytics.get_snapshots_at_cutoff(datetime.datetime.now(timezone.utc) - timedelta(days=7))
        past_30d_snaps = analytics.get_snapshots_at_cutoff(datetime.datetime.now(timezone.utc) - timedelta(days=30))
        
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
        
        logger.info("Generating secondary charts (Heatmaps, Trends, Diversity)...")
        activity_heatmap = analytics.get_activity_heatmap(days=30)
        clan_history = analytics.get_clan_trend(days=30)
        
        # Charts via Service
        boss_diversity = analytics.get_boss_diversity(latest_ids)
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
            "chart_boss_diversity": boss_diversity,
            "chart_raids": raids_performance,
            "chart_skills": skill_mastery,
            "chart_boss_trend": trending_boss,
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
            if not joined_dt and u_lower in min_timestamps:
                try:
                    joined_dt = min_timestamps[u_lower].timestamp
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

            # Construct User Object
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
                "favorite_boss": fav_boss_name, 
                "favorite_boss_img": fav_boss_img, 
                "favorite_boss_all_time": fav_boss_all_time_name,
                "favorite_boss_all_time_img": fav_boss_all_time_img,
                 "total_xp": curr.total_xp,
                 "total_boss": curr.total_boss_kills,
                 "msgs_7d": 0,
                 "msgs_30d": 0,
                 "msgs_total": 0
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
            
            if 'gowi' in u_clean:
                logger.debug(f"[DEBUG LOOP] Processing '{u_clean}'. Total: {user_obj['msgs_total']}, 7d: {user_obj['msgs_7d']}, 30d: {user_obj['msgs_30d']}")
            
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
        
        # --- GIT HUB PAGES EXPORT (docs/ folder) ---
        docs_dir = os.path.join(os.getcwd(), 'docs')
        if not os.path.exists(docs_dir):
            os.makedirs(docs_dir)

        import shutil
        
        # 1. Data (JSON)
        shutil.copy(OUTPUT_FILE, os.path.join(docs_dir, OUTPUT_FILE))

        # 1b. Data (JS)
        shutil.copy(js_output_file, os.path.join(docs_dir, js_output_file))
        
        # 2. HTML Dashboard -> index.html (for standard web serving)
        html_file = "clan_dashboard.html"
        if os.path.exists(html_file):
            shutil.copy(html_file, os.path.join(docs_dir, "index.html"))
    
        # 3. JS Logic
        js_file = "dashboard_logic.js"
        if os.path.exists(js_file):
            shutil.copy(js_file, os.path.join(docs_dir, js_file))
            
        # 4. Assets Folder
        assets_local = os.path.join(os.getcwd(), 'assets')
        assets_docs = os.path.join(docs_dir, 'assets')
        if os.path.exists(assets_local):
            if os.path.exists(assets_docs):
                shutil.rmtree(assets_docs) # Clean replace
            shutil.copytree(assets_local, assets_docs)
            
        logger.info(f"Dashboard deployed successfully to: docs/ (Ready for GitHub Pages)")
        
        # --- Drive Export ---
        if Config.LOCAL_DRIVE_PATH:
            from core.drive import DriveExporter
            DriveExporter.export_file(os.path.join("docs", "clan_data.js"))
            DriveExporter.export_file(os.path.join("docs", "clan_data.json"))
            DriveExporter.export_file(os.path.join("docs", "index.html"), target_filename="clan_dashboard.html")
            
            # Export Dependencies
            DriveExporter.export_file("dashboard_logic.js")
            if os.path.exists("ai_data.js"):
                 DriveExporter.export_file("ai_data.js")
            
            # Export Assets Folder (Recursive)
            assets_dir = os.path.join(os.getcwd(), "assets")
            if os.path.exists(assets_dir):
                for root, dirs, files in os.walk(assets_dir):
                    for file in files:
                        # Calculate relative path for target filename (e.g., assets/rank_minion.png)
                        abs_path = os.path.join(root, file)
                        rel_path = os.path.relpath(abs_path, os.getcwd())
                        DriveExporter.export_file(abs_path, target_filename=rel_path)

        if missing_assets:
            logger.warning(f"Missing {len(missing_assets)} assets: {sorted(list(missing_assets))}")

    except Exception as e:
        logger.error(f"Export failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if conn: conn.close()
        if db_session: db_session.close()

if __name__ == "__main__":
    print("DEBUG: Starting export_sqlite script...", flush=True)
    try:
        run_export()
        print("DEBUG: run_export completed.", flush=True)
    except Exception as e:
        print(f"DEBUG: Critical Error: {e}", flush=True)
        import traceback
        traceback.print_exc()
