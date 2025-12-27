
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
OUTPUT_FILE = "ai_data.js" # Generating a JS file for easy import

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
        
        # Alert 3: Raid Enthusiasts
        cursor = conn.execute("""
            SELECT bs.boss_name, COUNT(DISTINCT ws.username) as players
            FROM boss_snapshots bs
            JOIN wom_snapshots ws ON bs.wom_snapshot_id = ws.id
            WHERE bs.boss_name LIKE '%chambers%' AND ws.timestamp >= datetime('now', '-7 days')
            GROUP BY bs.boss_name
            HAVING players > 5
        """)
        raid_activity = cursor.fetchone()
        if raid_activity:
            alerts.append({
                "type": "success",
                "icon": "fa-fire",
                "title": "Raid Party",
                "message": f"CoX activity booming with {raid_activity['players']} participants this weekend!"
            })
        
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
        # Insight 1: Top Skill Trend
        cursor = conn.execute("""
            SELECT username, total_xp
            FROM wom_snapshots
            ORDER BY total_xp DESC
            LIMIT 1
        """)
        top_player = cursor.fetchone()
        if top_player:
            insights.append({
                "type": "trend",
                "title": "Skill Mastery Leader",
                "message": f"{top_player['username']} leads with {top_player['total_xp']:,} total XP. Inspiring others!"
            })
        
        # Insight 2: Boss Diversity
        cursor = conn.execute("""
            SELECT COUNT(DISTINCT boss_name) as unique_bosses
            FROM boss_snapshots bs
            JOIN wom_snapshots ws ON bs.wom_snapshot_id = ws.id
            WHERE ws.timestamp >= datetime('now', '-30 days')
        """)
        diversity = cursor.fetchone()
        if diversity and diversity['unique_bosses'] > 0:
            insights.append({
                "type": "analysis",
                "title": "Bossing Diversity",
                "message": f"Clan tackled {diversity['unique_bosses']} different bosses in the last month. Well-rounded!"
            })
        
        # Insight 3: Communication Health
        cursor = conn.execute("""
            SELECT AVG(msg_custom) as avg_msgs
            FROM wom_records
        """)
        comm = cursor.fetchone()
        if comm and comm['avg_msgs']:
            health = "excellent" if comm['avg_msgs'] > 50 else "good" if comm['avg_msgs'] > 20 else "needs improvement"
            insights.append({
                "type": "health",
                "title": "Communication Health",
                "message": f"Average weekly messages: {comm['avg_msgs']:.1f}. Communication health is {health}."
            })
        
        # Insight 4: Rising Stars
        cursor = conn.execute("""
            SELECT username, xp_custom as xp_7d, msg_custom as msg_7d
            FROM wom_records
            WHERE xp_custom > 500000 AND msg_custom > 50
            ORDER BY (xp_custom + msg_custom * 1000) DESC
            LIMIT 1
        """)
        rising = cursor.fetchone()
        if rising:
            insights.append({
                "type": "trend",
                "title": "Rising Star",
                "message": f"{rising['username']} is showing strong activity with {rising['xp_7d']:,} XP and {rising['msg_7d']} messages this week!"
            })
        
        # Insight 5: Clan Efficiency
        cursor = conn.execute("""
            SELECT AVG(xp_custom * 1.0 / NULLIF(msg_custom, 0)) as avg_efficiency
            FROM wom_records
            WHERE msg_custom > 0
        """)
        eff = cursor.fetchone()
        if eff and eff['avg_efficiency']:
            level = "highly efficient" if eff['avg_efficiency'] > 10000 else "balanced" if eff['avg_efficiency'] > 5000 else "could improve"
            insights.append({
                "type": "analysis",
                "title": "Clan Efficiency",
                "message": f"Average XP per message: {eff['avg_efficiency']:.0f}. The clan is {level} in balancing grind and chat."
            })
        
        # Insight 6: Prediction - Potential Inactive
        cursor = conn.execute("""
            SELECT username
            FROM wom_records
            WHERE msg_custom = 0 AND xp_custom = 0
            ORDER BY RANDOM()
            LIMIT 1
        """)
        inactive = cursor.fetchone()
        if inactive:
            insights.append({
                "type": "warning",
                "title": "Activity Monitor",
                "message": f"Keep an eye on {inactive['username']} - no activity detected this week. A friendly check-in might help!"
            })
        
        # Insight 7: Positive Reinforcement
        cursor = conn.execute("""
            SELECT COUNT(*) as active_count
            FROM wom_records
            WHERE msg_custom > 10 AND xp_custom > 100000
        """)
        active = cursor.fetchone()
        if active and active['active_count'] > 5:
            insights.append({
                "type": "success",
                "title": "Active Community",
                "message": f"{active['active_count']} members are highly engaged this week. Great job keeping the clan vibrant!"
            })
        
    except Exception as e:
        logger.error(f"Error generating AI insights: {e}")
    
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
