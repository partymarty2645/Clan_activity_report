"""
Dashboard Data Generator
========================
Exports clan statistics to clan_data.json for the HTML dashboard.
Refactored to use SQLAlchemy and `core.analytics.AnalyticsService`.
Includes Asset Mapping, Yap Star, Intensity Hero, and Fallback Logic.
"""

import json
import logging
import time
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Any

from core.analytics import AnalyticsService
from core.config import Config
from core.utils import normalize_user_string
from database.connector import SessionLocal
from database.models import WOMSnapshot, ClanMember

logger = logging.getLogger("DashboardExport")

# Non-standard roles mapping to nearest visual equivalent
CUSTOM_ROLE_MAP = {
    "prospector": "rank_opal.png",
    "star": "rank_jade.png",
    "defender": "rank_sapphire.png",
    "prodigy": "rank_emerald.png",
    "tztok": "rank_ruby.png",
    "zamorakian": "rank_diamond.png",
    "saradominist": "rank_dragonstone.png",
    "guthixian": "rank_onyx.png",
    "astral": "rank_sapphire.png",
    "cosmic": "rank_emerald.png",
    "blood": "rank_ruby.png",
    "soul": "rank_diamond.png",
    "wrath": "rank_dragonstone.png"
}

def get_asset_map() -> Dict[str, str]:
    """
    Scans the assets directory and returns a map of normalized names to filenames.
    e.g. {'zulrah': 'boss_zulrah.png', 'attack': 'skill_attack.png'}
    """
    assets_dir = Path(__file__).parent / "assets"
    if not assets_dir.exists():
        return {}
    
    mapping = {}
    for f in assets_dir.glob("*.png"):
        # normalize: boss_zulrah.png -> zulrah
        # rank_sergeant.png -> sergeant
        name = f.stem.lower()
        if name.startswith("boss_"):
            clean = name.replace("boss_", "").replace("_", " ")
            mapping[clean] = f.name
            mapping[clean.replace(" ", "_")] = f.name # handle both spaces and underscores
        elif name.startswith("skill_"):
            clean = name.replace("skill_", "")
            mapping[clean] = f.name
        elif name.startswith("rank_"):
            clean = name.replace("rank_", "")
            mapping[clean] = f.name
            
    return mapping

def generate_weekly_briefing(top_gainers, top_boss, outliers, trends):
    try:
        parts = []
        
        # 1. MVP
        if top_gainers:
            top = top_gainers[0]
            xp_mil = top['xp_7d'] / 1_000_000
            parts.append(f"**{top['username']}** is leading the charge with a massive **{xp_mil:.1f}M XP** gain this week.")
        
        # 2. Bossing
        if top_boss and top_boss[1] > 0:
            parts.append(f"The clan has been focusing on **{top_boss[0].replace('_', ' ').title()}**, claiming **{top_boss[1]:,}** kills.")
        
        # 3. Trend
        # Trends is now heatmap data list, check total volume vs previous? 
        # Simplified Check
        parts.append("Clan activity levels are stable.")
        
        # 4. Flavor
        grinders = len([o for o in outliers if o.get('status') == 'Silent Grinder'])
        if grinders > 0:
            parts.append(f"Our sensors detected **{grinders} Silent Grinders** working in the shadows.")
            
        return " ".join(parts)
    except Exception as e:
        logger.error(f"Briefing generation failed: {e}")
        return "Analysis complete. Systems functioning normally."

def export_dashboard_json() -> Path:
    """Export dashboard data to JSON file using AnalyticsService."""
    start_time = time.time()
    db = SessionLocal()
    analytics = AnalyticsService(db)
    
    try:
        logger.info("Starting dashboard export (Refactored)...")
        now_utc = datetime.now(timezone.utc)
        cutoff_7d = now_utc - timedelta(days=7)
        cutoff_30d = now_utc - timedelta(days=30)
        
        # 0. Load Assets Map
        asset_map = get_asset_map()
        
        # 0. Fetch Active Members (The Source of Truth)
        active_members = db.query(ClanMember).all()
        active_map = {m.username.lower(): m for m in active_members}
        logger.info(f"Loaded {len(active_members)} active members from DB.")

        # 1. Fetch Data
        latest_snaps = analytics.get_latest_snapshots()
        past_7d_snaps = analytics.get_snapshots_at_cutoff(cutoff_7d)
        past_30d_snaps = analytics.get_snapshots_at_cutoff(cutoff_30d)
        
        msg_counts_7d = analytics.get_message_counts(cutoff_7d)
        msg_counts_30d = analytics.get_message_counts(cutoff_30d)
        msg_counts_total = analytics.get_message_counts(datetime(2020, 1, 1))

        # 2. Calculate Gains
        gains_7d = analytics.calculate_gains(latest_snaps, past_7d_snaps)
        gains_30d = analytics.calculate_gains(latest_snaps, past_30d_snaps)
        
        # 3. User List Compilation
        user_list = []
        for user, snap in latest_snaps.items():
            # FILTER: ACTIVE ONLY
            if active_map and user not in active_map:
                continue 
            
            member_rec = active_map.get(user)
            role = member_rec.role.lower() if member_rec and member_rec.role else "recruit"
            
            # Use Asset Map for Rank Image
            # Priority: Direct Match -> Custom Map -> Recruit Fallback
            rank_img = asset_map.get(role)
            if not rank_img:
                # Try finding partial match in custom map keys?
                # or exact match in custom map
                rank_img = CUSTOM_ROLE_MAP.get(role, "rank_recruit.png")


            # Basic Stats
            xp_7 = gains_7d.get(user, {}).get('xp', 0)
            boss_7 = gains_7d.get(user, {}).get('boss', 0)
            xp_30 = gains_30d.get(user, {}).get('xp', 0)
            boss_30 = gains_30d.get(user, {}).get('boss', 0)
            
            # Msgs
            m_7 = msg_counts_7d.get(user, 0)
            m_30 = msg_counts_30d.get(user, 0)
            m_total = msg_counts_total.get(user, 0)
            
            # Days in Clan
            days_in_clan = 0
            joined_iso = None
            if member_rec and member_rec.joined_at:
                joined = member_rec.joined_at
                if joined.tzinfo is None: joined = joined.replace(tzinfo=timezone.utc)
                delta = now_utc - joined
                days_in_clan = max(0, delta.days)
                joined_iso = joined.isoformat()

            user_list.append({
                "username": user,
                "role": role,
                "rank_img": rank_img,
                "joined_at": joined_iso,
                "days_in_clan": days_in_clan, 
                "total_xp": snap.total_xp,
                "xp_7d": xp_7,
                "xp_30d": xp_30,
                "total_boss": snap.total_boss_kills,
                "boss_7d": boss_7,
                "boss_30d": boss_30,
                "msgs_7d": m_7,
                "msgs_30d": m_30,
                "msgs_total": m_total,
                "social_ratio": 0 # Calc later
            })
            
        # 4. Outliers & Rankings
        outliers = analytics.calculate_outliers(user_list)
        
        # 5. Top Lists (Calculation)
        top_xp = sorted([u for u in user_list], key=lambda x: x['xp_7d'], reverse=True)[:10]
        top_boss = sorted([u for u in user_list], key=lambda x: x['boss_7d'], reverse=True)[:10] # Changed to 7d for Intensity Hero check
        top_msg = sorted([u for u in user_list], key=lambda x: x['msgs_7d'], reverse=True)[:5]
        
        # --- LOGIC: The Yap Star (Rising Star) ---
        # Definition: Joined < 30 days ago, highest messages
        new_recruits = [u for u in user_list if u['days_in_clan'] <= 30]
        rising_star_data = {"name": "N/A", "days": 0, "msgs": 0}
        
        if new_recruits:
            # Sort by total messages (or 30d messages, same thing for new user)
            best_newbie = sorted(new_recruits, key=lambda x: x['msgs_total'], reverse=True)[0]
            if best_newbie['msgs_total'] > 0:
                rising_star_data = {
                    "name": best_newbie['username'],
                    "days": best_newbie['days_in_clan'],
                    "msgs": best_newbie['msgs_total']
                }

        # --- LOGIC: Intensity Hero (Top Boss 7d) ---
        # If top_boss list has data and > 0 kills
        intensity_hero_data = {"name": "N/A", "count": 0}
        if top_boss and top_boss[0]['boss_7d'] > 0:
            hero = top_boss[0]
            intensity_hero_data = {
                "name": hero['username'],
                "count": hero['boss_7d']
            }

        # --- FALLBACK SYSTEM ---
        # Check if we have weekly data. If not, fallback to All Time.
        is_fallback = False
        
        # Check XP
        if not top_xp or top_xp[0]['xp_7d'] == 0:
            is_fallback = True
            # Re-sort lists by Total
            top_xp = sorted(user_list, key=lambda x: x['total_xp'], reverse=True)[:10]
            # Verify we have totals
            if top_xp and top_xp[0]['total_xp'] == 0:
                 # Even totals are empty? Extremely unlikely unless DB empty.
                 pass

        # Check Boss
        if not top_boss or top_boss[0]['boss_7d'] == 0:
             # Fallback for Boss
             top_boss = sorted(user_list, key=lambda x: x['total_boss'], reverse=True)[:10]
             # If fallback active, Intensity Hero becomes Top Boss All Time
             if top_boss and top_boss[0]['total_boss'] > 0:
                 intensity_hero_data = {
                     "name": top_boss[0]['username'],
                     "count": top_boss[0]['total_boss'],
                     "label": "(All Time)"
                 }

        # Check Msg
        if not top_msg or top_msg[0]['msgs_7d'] == 0:
            top_msg = sorted(user_list, key=lambda x: x['msgs_total'], reverse=True)[:5]

        # 6. Detailed Boss Logic (Clan Wide) - Weekly
        clan_boss_weekly = analytics.get_detailed_boss_gains(latest_snaps, past_7d_snaps)
        best_weekly_boss_item = sorted(clan_boss_weekly.items(), key=lambda x: x[1], reverse=True)
        
        # Clean Boss Names using Map
        best_weekly_boss_data = {"name": "None", "count": 0, "img": "boss_pet_rock.png"}
        if best_weekly_boss_item and best_weekly_boss_item[0][1] > 0:
             raw_name = best_weekly_boss_item[0][0]
             clean_name = raw_name.replace('_', ' ').title()
             # Try to find asset
             # asset keys are lower, no 'boss_' prefix
             # raw_name usually matches e.g. 'zulrah' or 'the_nightmare'
             asset_key = raw_name.replace("_", " ").lower()
             img_file = asset_map.get(asset_key, "boss_pet_rock.png")
             
             best_weekly_boss_data = {
                 "name": clean_name,
                 "count": best_weekly_boss_item[0][1],
                 "img": img_file
             }

        # --- The Oracle (XP Predictions) ---
        MILESTONES = [100_000_000, 200_000_000, 500_000_000, 1_000_000_000, 2_000_000_000, 4_600_000_000]
        oracle_data = []
        for u in user_list:
            xp_rate = u['xp_7d'] / 7
            if xp_rate < 1000: continue # Ignore inactive

            curr = u['total_xp']
            # Find next milestone
            target = next((m for m in MILESTONES if curr < m), None)
            
            if target:
                needed = target - curr
                days = needed / xp_rate
                if days < 365 * 2: # Prediction overlap for 2 years
                    oracle_data.append({
                        "name": u['username'],
                        "days_left": round(days, 1),
                        "milestone": f"{target/1_000_000:.0f}M" if target < 1_000_000_000 else f"{target/1_000_000_000:.1f}B"
                    })
        
        # Sort by urgency
        oracle_data.sort(key=lambda x: x['days_left'])
        top_oracle = oracle_data[:5]

        # 8. Activity Trends (Heatmap)
        # Get heatmap for last 30 days
        heatmap_start = now_utc - timedelta(days=30)
        trends = analytics.get_activity_heatmap(heatmap_start) 

        # 9. Structure Final JSON
        data = {
            "lastUpdated": now_utc.strftime("%d-%m-%Y"),
            "lastUpdatedISO": now_utc.isoformat(),
            "isFallback": is_fallback,
            "assetMap": asset_map, # Pass map to frontend if needed, or we resolve backend
            "bossCards": {
                "weeklyTop": best_weekly_boss_data,
                "allTimeFavorite": {"name": "Kraken", "count": 0}, # Placeholder
                "intensityHero": intensity_hero_data
            },
            "risingStar": rising_star_data,
            "topMessenger": {
                "name": top_msg[0]['username'] if top_msg else "N/A",
                "messages": top_msg[0]['msgs_7d'] if top_msg and not is_fallback else top_msg[0]['msgs_total'] if top_msg else 0
            },
            "topXPGainer": {
                "name": top_xp[0]['username'] if top_xp else "N/A",
                "xp": top_xp[0]['xp_7d'] if top_xp and not is_fallback else top_xp[0]['total_xp'] if top_xp else 0
            },
            "topBossKiller": {
                "name": top_boss[0]['username'] if top_boss else "N/A",
                "kills": top_boss[0]['boss_7d'] if top_boss and not is_fallback else top_boss[0]['total_boss'] if top_boss else 0
            },
            "allMembers": user_list,
            "outliers": outliers, # Assuming outliers format is compatible
            "topXPGainers": top_xp[:10],
            "topMessagers": top_msg[:10],
            "activityTrends": trends,
            "oracle": top_oracle,
            "bingo": {
                "bosses": [
                    # Dynamic mapping possible here too
                    {"name": "Zulrah", "target": 1000, "current": clan_boss_weekly.get('zulrah', 0), "img": asset_map.get('zulrah', 'boss_zulrah.png')},
                    {"name": "Vorkath", "target": 1000, "current": clan_boss_weekly.get('vorkath', 0), "img": asset_map.get('vorkath', 'boss_vorkath.png')},
                    {"name": "The Nightmare", "target": 250, "current": clan_boss_weekly.get('the_nightmare', 0), "img": asset_map.get('the_nightmare', 'boss_the_nightmare.png')},
                    {"name": "Phantom Muspah", "target": 500, "current": clan_boss_weekly.get('phantom_muspah', 0), "img": asset_map.get('phantom_muspah', 'boss_phantom_muspah.png')},
                    {"name": "Duke Sucellus", "target": 300, "current": clan_boss_weekly.get('duke_sucellus', 0), "img": asset_map.get('duke_sucellus', 'boss_duke_sucellus.png')},
                    {"name": "Vardorvis", "target": 300, "current": clan_boss_weekly.get('vardorvis', 0), "img": asset_map.get('vardorvis', 'boss_vardorvis.png')},
                    {"name": "Leviathan", "target": 300, "current": clan_boss_weekly.get('the_leviathan', 0), "img": asset_map.get('the_leviathan', 'boss_the_leviathan.png')},
                    {"name": "Whisperer", "target": 300, "current": clan_boss_weekly.get('the_whisperer', 0), "img": asset_map.get('the_whisperer', 'boss_the_whisperer.png')}
                ]
            },
            "weeklyBriefing": generate_weekly_briefing(top_xp, (best_weekly_boss_data['name'], best_weekly_boss_data['count']), outliers, trends)
        }
        
        # 10. Write File
        output_path = Path(__file__).parent / "clan_data.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        # 10b. Write JS File (CORS Bypass)
        js_output_path = Path(__file__).parent / "clan_data.js"
        with open(js_output_path, 'w', encoding='utf-8') as f:
            json_str = json.dumps(data, ensure_ascii=False)
            f.write(f"window.dashboardData = {json_str};")
        logger.info(f"Dashboard JS data generated: {js_output_path}")

        elapsed = time.time() - start_time
        logger.info(f"Dashboard Export complete in {elapsed:.2f}s")
        return output_path

    except Exception as e:
        logger.error(f"Dashboard Export Failed: {e}")
        import traceback
        traceback.print_exc()
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    export_dashboard_json()
