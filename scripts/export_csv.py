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

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def export_csv_report():
    """Generates a CSV report of clan member activity."""
    conn = None
    try:
        db_path = Config.DB_FILE
        if not os.path.exists(db_path):
            logger.error(f"Database not found at {db_path}")
            return False

        conn = sqlite3.connect(db_path)
        logger.info(f"Connected to database: {db_path}")

        # 1. Fetch Membership Data
        # We'll key everything by username for easy merging
        df_members = pd.read_sql_query("SELECT username, role, joined_at FROM clan_members", conn)
        
        # 2. Fetch Latest Activity Snapshot (XP, Bosses via JSON potentially?)
        # Or re-use the logic from export_sqlite.py/report_sqlite.py to get "Gains"
        # For a simple CSV, users usually want: Name, Role, Total XP, Total Boss, Total Messages, Join Date
        
        # Let's use a consolidated query or existing views if possible.
        # Queries.GET_LATEST_SNAPSHOTS gives us latest XP
        
        cursor = conn.cursor()
        
        # Get Latest Snapshots
        cursor.execute(Queries.GET_LATEST_SNAPSHOTS)
        latest_snaps = {}
        for row in cursor.fetchall():
            # id, player_id, timestamp, total_xp, total_boss, overall_rank
            latest_snaps[row[1]] = { # player_id is FK, but we need username linkage
                'xp': row[3], 
                'boss': row[4],
                'rank': row[5],
                'snapshot_id': row[0]
            }
        
        # We need a map of player_id -> username or join with members
        # The GET_LATEST_SNAPSHOTS query in Queries.py might need checking. 
        # Actually, let's write a targeted JOIN query for the CSV to be efficient.
        
        csv_query = """
        SELECT 
            m.username,
            m.role,
            m.joined_at,
            COALESCE(ws.total_xp, 0) as total_xp,
            COALESCE(ws.total_boss_kills, 0) as total_boss_kills,
            COALESCE(ws.overall_rank, 0) as overall_rank,
            (SELECT COUNT(*) FROM discord_messages dm WHERE dm.username = m.username) as total_messages
        FROM clan_members m
        LEFT JOIN wom_snapshots ws ON m.id = ws.player_id
        WHERE ws.timestamp = (
            SELECT MAX(timestamp) FROM wom_snapshots WHERE player_id = m.id
        ) OR ws.player_id IS NULL
        GROUP BY m.username
        ORDER BY total_xp DESC
        """
        
        df_report = pd.read_sql_query(csv_query, conn)
        
        # Cleanup Dates
        df_report['joined_at'] = pd.to_datetime(df_report['joined_at']).dt.strftime('%Y-%m-%d')
        
        # Output Path
        output_dir = os.path.join(Config.PROJECT_ROOT, 'data', 'exports')
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d')
        filename = f"clan_export_{timestamp}.csv"
        file_path = os.path.join(output_dir, filename)
        
        # Save CSV
        df_report.to_csv(file_path, index=False)
        logger.info(f"CSV Report generated: {file_path}")
        
        # Also save a "latest" version for the dashboard to link to easily?
        # Or simply 'clan_data.csv' that is always overwritten? 
        # User wants "Download CSV" on dashboard. A static link is easiest.
        static_path = os.path.join(output_dir, "clan_data.csv")
        df_report.to_csv(static_path, index=False)
        logger.info(f"Static CSV updated: {static_path}")
        
        # Copy to Drive if configured?
        # report_sqlite.py does it. Let's stick to local first, dashboard can serve it if we put it in assets?
        # Actually, the dashboard is static HTML. It can't serve files from 'data/exports' unless that folder is deployed.
        # We should copy 'clan_data.csv' to the deployment folder (GDrive or just 'dist' folder logic).
        
        if Config.GDRIVE_PATH and os.path.exists(Config.GDRIVE_PATH):
            import shutil
            gdrive_csv = os.path.join(Config.GDRIVE_PATH, "clan_data.csv")
            shutil.copy2(static_path, gdrive_csv)
            logger.info(f"Copied CSV to Drive: {gdrive_csv}")

        return True

    except Exception as e:
        logger.error(f"CSV Export Failed: {e}")
        return False
    finally:
        if conn: conn.close()

if __name__ == "__main__":
    export_csv_report()
