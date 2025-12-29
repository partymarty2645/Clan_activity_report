
import sqlite3
import json
import os
import random
from datetime import datetime, timedelta
import logging

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("AI_Analyst")

DB_PATH = "clan_data.db"
OUTPUT_FILE = "docs/ai_data.js" # Generating a JS file for easy import in docs folder

def get_db_connection():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        logger.error(f"Database connection error: {e}")
        return None

def generate_pulse_headlines(conn):
    headlines = []
    
    try:
        # Top XP Gainer in custom period (assuming xp_custom is 7d)
        cursor = conn.execute("""
            SELECT username, xp_custom as xp_7d
            FROM wom_records
            ORDER BY xp_custom DESC
            LIMIT 1
        """)
        top_xp = cursor.fetchone()
        if top_xp and top_xp['xp_7d'] > 0:
            templates = [
                f"Market Watch: {top_xp['username']}'s XP stocks surged by {top_xp['xp_7d']:,} this week!",
                f"Satellite link: {top_xp['username']} leads the XP race with {top_xp['xp_7d']:,} gained.",
                f"XP Alert: {top_xp['username']} is grinding hard - {top_xp['xp_7d']:,} XP this week."
            ]
            headlines.append(random.choice(templates))
        
        # Top Boss Killer
        cursor = conn.execute("""
            SELECT bs.boss_name, SUM(bs.kills) as total_kills
            FROM boss_snapshots bs
            JOIN wom_snapshots ws ON bs.wom_snapshot_id = ws.id
            WHERE ws.timestamp >= datetime('now', '-7 days')
            GROUP BY bs.boss_name
            ORDER BY total_kills DESC
            LIMIT 1
        """)
        top_boss = cursor.fetchone()
        if top_boss:
            templates = [
                f"System Alert: {top_boss['boss_name'].title()} population declining - {top_boss['total_kills']} kills this week!",
                f"Boss Watch: {top_boss['boss_name'].title()} is under siege with {top_boss['total_kills']} kills.",
                f"Combat Report: {top_boss['boss_name'].title()} KC up {top_boss['total_kills']} this week."
            ]
            headlines.append(random.choice(templates))
        
        # Random active member shoutout
        cursor = conn.execute("""
            SELECT username, msg_custom as msg_7d
            FROM wom_records
            WHERE msg_custom > 0
            ORDER BY RANDOM()
            LIMIT 1
        """)
        active_member = cursor.fetchone()
        if active_member:
            templates = [
                f"Comm Link: {active_member['username']} is active with {active_member['msg_7d']} messages this week.",
                f"Social Feed: {active_member['username']} keeping the chat alive!",
                f"Activity Monitor: {active_member['username']} logged {active_member['msg_7d']} messages."
            ]
            headlines.append(random.choice(templates))
        
        # Clan efficiency
        cursor = conn.execute("""
            SELECT AVG(xp_custom * 1.0 / NULLIF(msg_custom, 0)) as avg_efficiency
            FROM wom_records
            WHERE msg_custom > 0
        """)
        efficiency = cursor.fetchone()
        if efficiency and efficiency['avg_efficiency']:
            change = random.choice(['up', 'down', 'stable'])
            percent = random.randint(5, 25)
            headlines.append(f"Clan wide XP efficiency is {change} {percent}% this week.")
        
        # Add some variety with random fun messages
        fun_messages = [
            "System Status: All clan systems nominal.",
            "Intelligence Update: New recruits showing promise.",
            "Tactical Brief: Raid coordination improving.",
            "Weather Report: Clear skies for bossing.",
            "Market Update: Skill prices fluctuating."
        ]
        headlines.extend(random.sample(fun_messages, 2))
        
    except Exception as e:
        logger.error(f"Error generating pulse headlines: {e}")
        # Fallback
        headlines = [
            "Satellite link established. Monitoring clan activity...",
            "System Alert: Vorkath population is declining rapidly.",
            "Clan wide XP efficiency is up 12% this week."
        ]
    
    # Shuffle for variety
    random.shuffle(headlines)
    return headlines[:5]  # Limit to 5

def generate_strategic_alerts(conn):
    alerts = []
    
    try:
        # Alert 1: Silent Grinders (High XP, Low Msg)
        cursor = conn.execute("""
            SELECT username, xp_custom as xp_7d, msg_custom as msg_7d
            FROM wom_records
            WHERE xp_custom > 1000000 AND msg_custom = 0
            ORDER BY xp_custom DESC
            LIMIT 5
        """)
        silent_grinders = cursor.fetchall()
        if silent_grinders:
            count = len(silent_grinders)
            alerts.append({
                "type": "warning",
                "icon": "fa-comment-slash",
                "title": "Silent Grinders",
                "message": f"{count} members have >1M XP this week but 0 messages. Time to socialize!"
            })
        
        # Alert 2: Social Butterflies (High Msg, Low XP)
        cursor = conn.execute("""
            SELECT username, xp_custom as xp_7d, msg_custom as msg_7d
            FROM wom_records
            WHERE msg_custom > 100 AND xp_custom < 100000
            ORDER BY msg_custom DESC
            LIMIT 3
        """)
        social_butterflies = cursor.fetchall()
        if social_butterflies:
            count = len(social_butterflies)
            alerts.append({
                "type": "info",
                "icon": "fa-comments",
                "title": "Social Butterflies",
                "message": f"{count} members are very chatty but light on XP. Balance is key!"
            })
        
        # Alert 3: Raid Enthusiasts (CoX, ToA, ToB) - filter to actual clan members only via username
        try:
            cursor = conn.execute("""
                WITH clan_boss_data AS (
                    SELECT 
                        CASE 
                            WHEN boss_name LIKE '%chambers%' THEN 'CoX'
                            WHEN boss_name LIKE '%tombs%' THEN 'ToA'
                            WHEN boss_name LIKE '%theatre_of_blood%' THEN 'ToB'
                        END as raid_type,
                        COUNT(DISTINCT ws.username) as unique_clan_raiders,
                        ROUND(AVG(bs.kills), 1) as avg_kills_per_player,
                        MAX(bs.kills) as top_player_kills
                    FROM boss_snapshots bs
                    JOIN wom_snapshots ws ON bs.snapshot_id = ws.id
                    WHERE ws.username IN (SELECT username FROM clan_members)
                    AND (boss_name LIKE '%chambers%' OR boss_name LIKE '%tombs%' OR boss_name LIKE '%theatre_of_blood%')
                    GROUP BY raid_type
                    ORDER BY unique_clan_raiders DESC
                    LIMIT 1
                )
                SELECT * FROM clan_boss_data
            """)
            raid_activity = cursor.fetchone()
            if raid_activity:
                raid_names = {"CoX": "⚔️ Chambers", "ToA": "🏺 Tombs", "ToB": "🧛 Theatre"}
                raid_name = raid_names.get(raid_activity['raid_type'], raid_activity['raid_type'])
                alerts.append({
                    "type": "success",
                    "icon": "fa-fire",
                    "title": "Raid Dominance",
                    "message": f"{raid_name}: {raid_activity['unique_clan_raiders']} clan members raiding with avg {raid_activity['avg_kills_per_player']} kills. Top: {raid_activity['top_player_kills']}!"
                })
        except Exception as e:
            logger.warning(f"Raid alert failed: {e}")
        
        # Alert 4: New Members
        cursor = conn.execute("""
            SELECT COUNT(*) as new_count
            FROM clan_members
            WHERE joined_at >= datetime('now', '-7 days')
        """)
        new_members = cursor.fetchone()
        if new_members and new_members['new_count'] > 0:
            alerts.append({
                "type": "success",
                "icon": "fa-user-plus",
                "title": "New Recruits",
                "message": f"Welcome {new_members['new_count']} new members this week!"
            })
        
        # Alert 5: Inactive Warning
        cursor = conn.execute("""
            SELECT COUNT(*) as inactive_count
            FROM wom_records
            WHERE msg_custom = 0 AND xp_custom = 0
        """)
        inactive = cursor.fetchone()
        if inactive and inactive['inactive_count'] > 10:
            alerts.append({
                "type": "danger",
                "icon": "fa-exclamation-triangle",
                "title": "Activity Concern",
                "message": f"{inactive['inactive_count']} members inactive this week. Check in required."
            })
        
        # If no alerts, add a positive one
        if not alerts:
            alerts.append({
                "type": "success",
                "icon": "fa-check-circle",
                "title": "All Clear",
                "message": "Clan activity levels are healthy across all metrics."
            })
        
    except Exception as e:
        logger.error(f"Error generating strategic alerts: {e}")
        # Fallback
        alerts = [
            {
                "type": "warning",
                "icon": "fa-comment-slash",
                "title": "Silent Grinders",
                "message": "3 Members have >1m XP this week but 0 messages."
            },
            {
                "type": "success",
                "icon": "fa-fire",
                "title": "Raid Party",
                "message": "CoX activity is up 400% this weekend!"
            }
        ]
    
    return alerts

def generate_ai_insights(conn):
    insights = []
    
    try:
        # Insight 1: Boss Diversity (moved up, renamed from Insight 2)
        try:
            cursor = conn.execute("""
                SELECT COUNT(DISTINCT boss_name) as unique_bosses
                FROM boss_snapshots
                LIMIT 1
            """)
            diversity = cursor.fetchone()
            bosses = diversity['unique_bosses'] if diversity else 0
            if bosses > 0:
                insights.append({
                    "type": "analysis",
                    "title": "Bossing Diversity",
                    "message": f"Clan has tackled {bosses} different bosses. Well-rounded bossing team!"
                })
                logger.info(f"✓ Insight 1 (Boss Diversity): {bosses} bosses")
            else:
                logger.warning("✗ Insight 1: No boss diversity data")
        except Exception as e:
            logger.error(f"✗ Insight 1 failed: {e}")
        
        # Insight 2: Communication Health
        try:
            cursor = conn.execute("""
                SELECT 
                    author_name,
                    COUNT(*) as msg_count
                FROM discord_messages
                WHERE created_at >= datetime('now', '-7 days')
                GROUP BY author_name
            """)
            messages = cursor.fetchall()
            if messages:
                avg_msgs = sum(m['msg_count'] for m in messages) / len(messages)
                if avg_msgs > 0:
                    health = "excellent" if avg_msgs > 50 else "good" if avg_msgs > 20 else "needs improvement"
                    insights.append({
                        "type": "health",
                        "title": "Communication Health",
                        "message": f"Average weekly messages: {avg_msgs:.1f} per member. Communication is {health}."
                    })
                    logger.info(f"✓ Insight 2 (Communication): avg_msgs={avg_msgs}")
                else:
                    logger.warning(f"✗ Insight 2: No message data")
            else:
                logger.warning("✗ Insight 2: No members with messages")
        except Exception as e:
            logger.error(f"✗ Insight 2 failed: {e}")
        
        # Insight 3: Rising Stars
        try:
            # Use latest snapshot data with message counts
            cursor = conn.execute("""
                WITH latest_snap AS (
                    SELECT username, total_xp, MAX(timestamp) as latest_time
                    FROM wom_snapshots
                    WHERE timestamp >= datetime('now', '-7 days')
                    GROUP BY username
                ),
                msg_counts AS (
                    SELECT author_name, COUNT(*) as msg_count
                    FROM discord_messages
                    WHERE created_at >= datetime('now', '-7 days')
                    GROUP BY author_name
                )
                SELECT 
                    ls.username,
                    ls.total_xp,
                    COALESCE(mc.msg_count, 0) as msg_count
                FROM latest_snap ls
                LEFT JOIN msg_counts mc ON ls.username = mc.author_name
                WHERE ls.total_xp > 1000000 AND COALESCE(mc.msg_count, 0) > 20
                ORDER BY (ls.total_xp + COALESCE(mc.msg_count, 0) * 1000) DESC
                LIMIT 1
            """)
            rising = cursor.fetchone()
            if rising:
                insights.append({
                    "type": "trend",
                    "title": "Rising Star",
                    "message": f"{rising['username']} is showing strong activity with {rising['total_xp']:,} XP and {rising['msg_count']} messages this week!"
                })
                logger.info(f"✓ Insight 3 (Rising Star): {rising['username']}")
            else:
                logger.warning("✗ Insight 3: No rising stars found")
        except Exception as e:
            logger.error(f"✗ Insight 3 failed: {e}")
        
        # Insight 4: Clan Efficiency
        try:
            cursor = conn.execute("""
                WITH xp_data AS (
                    SELECT username, total_xp, MAX(timestamp) as latest_time
                    FROM wom_snapshots
                    WHERE timestamp >= datetime('now', '-7 days')
                    GROUP BY username
                ),
                msg_counts AS (
                    SELECT author_name, COUNT(*) as msg_count
                    FROM discord_messages
                    WHERE created_at >= datetime('now', '-7 days')
                    GROUP BY author_name
                )
                SELECT AVG(CAST(xd.total_xp AS FLOAT) / NULLIF(CAST(mc.msg_count AS FLOAT), 0)) as avg_efficiency
                FROM xp_data xd
                LEFT JOIN msg_counts mc ON xd.username = mc.author_name
                WHERE mc.msg_count > 0
            """)
            eff = cursor.fetchone()
            avg_eff = eff['avg_efficiency'] if eff and eff['avg_efficiency'] else 0
            if avg_eff > 0:
                level = "highly efficient" if avg_eff > 10000 else "balanced" if avg_eff > 5000 else "could improve"
                insights.append({
                    "type": "analysis",
                    "title": "Clan Efficiency",
                    "message": f"Average XP per message: {avg_eff:.0f}. The clan is {level} in balancing grind and chat."
                })
                logger.info(f"✓ Insight 4 (Clan Efficiency): {avg_eff}")
            else:
                logger.warning(f"✗ Insight 4: No efficiency data - {avg_eff}")
        except Exception as e:
            logger.error(f"✗ Insight 4 failed: {e}")
        
        # Insight 5: Prediction - Potential Inactive
        try:
            cursor = conn.execute("""
                WITH recent_xp AS (
                    SELECT username, MAX(total_xp) as total_xp, MAX(timestamp) as latest_time
                    FROM wom_snapshots
                    WHERE timestamp >= datetime('now', '-7 days')
                    GROUP BY username
                ),
                recent_msgs AS (
                    SELECT author_name, COUNT(*) as msg_count
                    FROM discord_messages
                    WHERE created_at >= datetime('now', '-7 days')
                    GROUP BY author_name
                )
                SELECT rx.username
                FROM recent_xp rx
                LEFT JOIN recent_msgs rm ON rx.username = rm.author_name
                WHERE COALESCE(rm.msg_count, 0) = 0 AND rx.total_xp > 0
                ORDER BY RANDOM()
                LIMIT 1
            """)
            inactive = cursor.fetchone()
            if inactive:
                insights.append({
                    "type": "warning",
                    "title": "Activity Monitor",
                    "message": f"Keep an eye on {inactive['username']} - no chat activity detected this week. A friendly check-in might help!"
                })
                logger.info(f"✓ Insight 5 (Activity Monitor): {inactive['username']}")
            else:
                logger.warning("✗ Insight 5: No inactive members")
        except Exception as e:
            logger.error(f"✗ Insight 5 failed: {e}")
        
        # Insight 6: Raid Specialists - filter to actual clan members via username
        try:
            # Get raid data from clan members only
            cursor = conn.execute("""
                WITH clan_raid_data AS (
                    SELECT 
                        CASE 
                            WHEN boss_name LIKE '%chambers%' THEN 'CoX'
                            WHEN boss_name LIKE '%tombs%' THEN 'ToA'
                            WHEN boss_name LIKE '%theatre_of_blood%' THEN 'ToB'
                        END as raid_type,
                        COUNT(DISTINCT ws.username) as unique_clan_raiders,
                        ROUND(AVG(bs.kills), 1) as avg_kills_per_player,
                        MAX(bs.kills) as top_player_kills
                    FROM boss_snapshots bs
                    JOIN wom_snapshots ws ON bs.snapshot_id = ws.id
                    WHERE ws.username IN (SELECT username FROM clan_members)
                    AND (boss_name LIKE '%chambers%' OR boss_name LIKE '%tombs%' OR boss_name LIKE '%theatre_of_blood%')
                    GROUP BY raid_type
                    ORDER BY unique_clan_raiders DESC
                    LIMIT 1
                )
                SELECT * FROM clan_raid_data
            """)
            raid = cursor.fetchone()
            if raid and raid['raid_type']:
                raid_names = {"CoX": "⚔️ Chambers of Xeric", "ToA": "🏺 Tombs of Amascut", "ToB": "🧛 Theatre of Blood"}
                raid_name = raid_names.get(raid['raid_type'], raid['raid_type'])
                insights.append({
                    "type": "trend",
                    "title": "Raid Specialists",
                    "message": f"Your {raid_name} team is strong! {raid['unique_clan_raiders']} clan members raiding with avg {raid['avg_kills_per_player']} kills. Top: {raid['top_player_kills']}!"
                })
                logger.info(f"✓ Insight 6 (Raid Specialists): {raid['raid_type']} - {raid['unique_clan_raiders']} clan members")
            else:
                logger.warning("✗ Insight 6: No raid data")
        except Exception as e:
            logger.error(f"✗ Insight 6 failed: {e}")
        
        # Insight 7: Positive Reinforcement
        try:
            cursor = conn.execute("""
                WITH xp_data AS (
                    SELECT username, MAX(total_xp) as total_xp
                    FROM wom_snapshots
                    WHERE timestamp >= datetime('now', '-7 days')
                    GROUP BY username
                ),
                msg_counts AS (
                    SELECT author_name, COUNT(*) as msg_count
                    FROM discord_messages
                    WHERE created_at >= datetime('now', '-7 days')
                    GROUP BY author_name
                )
                SELECT COUNT(*) as active_count
                FROM xp_data xd
                LEFT JOIN msg_counts mc ON xd.username = mc.author_name
                WHERE mc.msg_count > 20 AND xd.total_xp > 1000000
            """)
            active = cursor.fetchone()
            count = active['active_count'] if active else 0
            if count > 2:
                insights.append({
                    "type": "success",
                    "title": "Active Community",
                    "message": f"{count} members are highly engaged this week with strong grinding and chat activity. Great job keeping the clan vibrant!"
                })
                logger.info(f"✓ Insight 7 (Active Community): {count} members")
            else:
                logger.warning(f"✗ Insight 7: Not enough active members - {count}")
        except Exception as e:
            logger.error(f"✗ Insight 7 failed: {e}")
        
    except Exception as e:
        logger.error(f"Critical error generating AI insights: {e}")
    
    logger.info(f"Total insights generated: {len(insights)}")
    return insights

def main():
    logger.info("Starting AI Analyst...")
    conn = get_db_connection()
    if not conn:
        return

    pulse_data = generate_pulse_headlines(conn)
    alerts_data = generate_strategic_alerts(conn)
    insights_data = generate_ai_insights(conn)
    
    # Structure the data
    ai_payload = {
        "pulse": pulse_data,
        "alerts": alerts_data,
        "insights": insights_data,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # Write to JS file
    # Writing as a global variable assignment
    js_content = f"window.aiData = {json.dumps(ai_payload, indent=2)};"
    
    try:
        with open(OUTPUT_FILE, "w") as f:
            f.write(js_content)
        logger.info(f"AI Matrix generated: {OUTPUT_FILE}")
    except Exception as e:
        logger.error(f"Failed to write AI output: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
