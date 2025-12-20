import asyncio
import logging
import sys
import shutil
import os
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Tuple

# Harvest client needed for member list
from harvest import wom_client 
from core.config import Config
from core.analytics import AnalyticsService
from database.connector import SessionLocal, init_db
from reporting.excel import reporter
# from reporting.drive import DriveManager # Removed

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("ReportGenerator")

class DataValidator:
    """Helper class to validate data integrity before reporting."""
    @staticmethod
    def validate_report_data(data: List[Dict]) -> Tuple[List[Dict], List[str]]:
        warnings = []
        clean_data = []
        for row in data:
            if row.get('Username') in [None, '']:
                continue
            
            # Clamp negative gains
            for k, v in row.items():
                if isinstance(v, (int, float)) and v < 0:
                     if 'Gained' in k or 'kills' in k:
                        row[k] = 0
            
            clean_data.append(row)
            
        return clean_data, warnings

async def run_report(close_client=True):
    """
    Main entry point for generating the Excel report.
    """
    logger.info("Starting Clan Report Generation...")
    
    # 1. Initialize DB & Service
    init_db()
    db = SessionLocal()
    analytics = AnalyticsService(db)
    
    try:
        # 2. Fetch Current Clan Members (Source of Truth: Local DB -> API -> Fallback)
        logger.info("Loading member list...")
        from database.models import ClanMember
        
        usernames = []
        member_map = {}
        
        # Strategy A: Local Refresh (Preferred)
        try:
            db_members = db.query(ClanMember).all()
            if db_members:
                logger.info(f"Loaded {len(db_members)} members from verified local cache (ClanMember table).")
                for m in db_members:
                    usernames.append(m.username)
                    member_map[m.username.lower()] = m
            else:
                logger.warning("Local member cache is empty. Attempting API fetch...")
                members = await wom_client.get_group_members(Config.WOM_GROUP_ID)
                member_map = {m.username.lower(): m for m in members}
                usernames = list(member_map.keys())
                
        except Exception as e:
             logger.error(f"Error loading members: {e}")
             
        # Strategy B: Fallback to active snapshots (Ghost Risk but better than crash)
        if not usernames:
             logger.warning("CRITICAL: Member list empty. Falling back to recent snapshots (May include ghosts!)")
             latest_snaps = analytics.get_latest_snapshots()
             usernames = list(latest_snaps.keys())

        # 4. Generate Report
        logger.info("Generating Excel Report with Master Sheet Schema...")
        
        # We pass the analytics service and the member map (metadata) 
        # The ExcelReporter now handles all data fetching for consistent 7d/30d/90d/Yearly logic.
        reporter.generate(analytics, metadata=member_map)

        # 5. Drive Sync (if configured)
        if Config.LOCAL_DRIVE_PATH and os.path.exists(Config.LOCAL_DRIVE_PATH):
            try:
                target = os.path.join(Config.LOCAL_DRIVE_PATH, Config.OUTPUT_FILE_XLSX)
                shutil.copy(Config.OUTPUT_FILE_XLSX, target)
                logger.info(f"Synced to Drive: {target}")
            except Exception as e:
                logger.error(f"Drive Sync Failed: {e}")

    except Exception as e:
        logger.error(f"Report Run Failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()
        if close_client:
            await wom_client.close()

if __name__ == "__main__":
    # Async wrapper for Python 3.7+
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run_report())
    finally:
        loop.close()
