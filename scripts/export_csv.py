import sqlite3
import pandas as pd
import os
import json
import logging
from datetime import datetime, timezone
import sys

# Add parent directory to path to import core modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.config import Config
from data.queries import Queries
from database.connector import SessionLocal
from services.user_access_service import UserAccessService

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def export_csv_report():
    """Generates a CSV report of clan member activity using UserAccessService."""
    conn = None
    session = None
    try:
        logger.info("Starting CSV Data Export with UserAccessService...")
        db_path = Config.DB_FILE
        if not os.path.exists(db_path):
            logger.error(f"Database not found at {db_path}")
            return False

        # Use UserAccessService for optimized member data retrieval
        session = SessionLocal()
        user_service = UserAccessService(session)
        
        # Get all active members with comprehensive stats
        active_members = user_service.get_all_active_members(days_back=30)
        logger.info(f"Retrieved {len(active_members)} active members via UserAccessService")
        
        # Convert to pandas DataFrame for CSV export
        member_data = []
        for member_stats in active_members:
            # Get additional profile data
            profile = user_service.get_user_profile(member_stats.user_id)
            
            member_data.append({
                'username': member_stats.username,
                'role': profile.role if profile else 'Member',
                'joined_at': profile.joined_at.isoformat() if profile and profile.joined_at else None,
                'total_xp': member_stats.total_xp,
                'total_boss_kills': member_stats.total_boss_kills,
                'xp_7d': member_stats.xp_7d,
                'xp_30d': member_stats.xp_30d,
                'boss_7d': member_stats.boss_7d,
                'boss_30d': member_stats.boss_30d,
                'msgs_7d': member_stats.msgs_7d,
                'msgs_30d': member_stats.msgs_30d
            })
        
        # Create DataFrame from UserAccessService data
        df_members = pd.DataFrame(member_data)
        logger.info(f"Created DataFrame with {len(df_members)} member records")
        
        # 2. Fetch Latest Activity Snapshot (XP, Bosses via JSON potentially?)
        # Or re-use the logic from export_sqlite.py/report_sqlite.py to get "Gains"
        # For a simple CSV, users usually want: Name, Role, Total XP, Total Boss, Total Messages, Join Date
        
        # Let's use a consolidated query or existing views if possible.
        # Queries.GET_LATEST_SNAPSHOTS gives us latest XP
        
        cursor = conn.cursor()
        
        # Build a targeted JOIN query for the CSV to be efficient.
        
        csv_query = """
        SELECT 
            m.username,
            m.role,
            m.joined_at,
            COALESCE(ws.total_xp, 0) as total_xp,
            COALESCE(ws.total_boss_kills, 0) as total_boss_kills,
            (SELECT COUNT(*) FROM discord_messages dm WHERE lower(dm.author_name) = lower(m.username)) as total_messages
        FROM clan_members m
        LEFT JOIN wom_snapshots ws ON m.id = ws.user_id
        WHERE ws.timestamp = (
            SELECT MAX(timestamp) FROM wom_snapshots WHERE user_id = m.id
        ) OR ws.user_id IS NULL
        GROUP BY m.username
        ORDER BY total_xp DESC
        """
        
        df_report = pd.read_sql_query(csv_query, conn)
        
        # Cleanup Dates
        df_report['joined_at'] = pd.to_datetime(df_report['joined_at']).dt.strftime('%Y-%m-%d')
        
        # Output Path
        # Use project root fallback if not configured
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_dir = os.path.join(base_dir, 'data', 'exports')
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d')
        filename = f"clan_export_{timestamp}.csv"
        file_path = os.path.join(output_dir, filename)
        
        # Save CSV
        df_report.to_csv(file_path, index=False)
        print(f"Snapshot saved: {os.path.basename(file_path)}")
        
        # Also save a "latest" version for the dashboard to link to easily?
        # Or simply 'clan_data.csv' that is always overwritten? 
        # User wants "Download CSV" on dashboard. A static link is easiest.
        static_path = os.path.join(output_dir, "clan_data.csv")
        df_report.to_csv(static_path, index=False)
        print(f"Static CSV updated (ready for dashboard).")
        
        # Copy to Drive if configured?
        # report_sqlite.py does it. Let's stick to local first, dashboard can serve it if we put it in assets?
        # Actually, the dashboard is static HTML. It can't serve files from 'data/exports' unless that folder is deployed.
        # We should copy 'clan_data.csv' to the deployment folder (GDrive or just 'dist' folder logic).
        
        if Config.LOCAL_DRIVE_PATH:
            from core.drive import DriveExporter
            DriveExporter.export_file(static_path, target_filename="clan_data.csv")

        return True

    except Exception as e:
        logger.error(f"CSV Export Failed: {e}")
        return False
    finally:
        if conn: conn.close()

if __name__ == "__main__":
    export_csv_report()
