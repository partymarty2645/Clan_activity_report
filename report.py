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
        # 2. Fetch Current Clan Members from WOM
        logger.info("Fetching members from WOM...")
        try:
            members = await wom_client.get_group_members(Config.WOM_GROUP_ID)
            member_map = {m.username.lower(): m for m in members}
            usernames = list(member_map.keys())
        except Exception as e:
            logger.error(f"Failed to fetch members: {e}")
            logger.info("Fallback: using all users in latest snapshots.")
            latest_all = analytics.get_latest_snapshots()
            usernames = list(latest_all.keys())
            member_map = {} 
        
        logger.info(f"Generating report for {len(usernames)} members...")
        
        # 3. Define Time Periods
        now_utc = datetime.now(timezone.utc)
        cutoff_7d = now_utc - timedelta(days=7)
        cutoff_30d = now_utc - timedelta(days=30)
        cutoff_70d = now_utc - timedelta(days=70)
        cutoff_150d = now_utc - timedelta(days=150)
        
        # 4. Fetch Data via AnalyticsService
        logger.info("Fetching snapshots...")
        latest = analytics.get_latest_snapshots()
        past_7d = analytics.get_snapshots_at_cutoff(cutoff_7d)
        past_30d = analytics.get_snapshots_at_cutoff(cutoff_30d)
        past_70d = analytics.get_snapshots_at_cutoff(cutoff_70d)
        past_150d = analytics.get_snapshots_at_cutoff(cutoff_150d)
        
        logger.info("Counting messages...")
        msgs_7 = analytics.get_message_counts(cutoff_7d)
        msgs_30 = analytics.get_message_counts(cutoff_30d)
        msgs_70 = analytics.get_message_counts(cutoff_70d)
        msgs_150 = analytics.get_message_counts(cutoff_150d)
        msgs_all = analytics.get_message_counts(datetime(2020, 1, 1))
        
        # 5. Calculate Gains
        logger.info("Calculating gains...")
        gains_7d = analytics.calculate_gains(latest, past_7d)
        gains_30d = analytics.calculate_gains(latest, past_30d)
        gains_70d = analytics.calculate_gains(latest, past_70d)
        gains_150d = analytics.calculate_gains(latest, past_150d)
        
        # 6. Compile Data List
        data_list = []
        for user in usernames:
            m = member_map.get(user.lower())
            role = m.role if m else "member"
            joined = m.joined_at if m else None
            display_name = m.username if m else user 
            
            curr = latest.get(user.lower()) # Key is normalized in map
            if not curr: 
                 # Try original casing if normalized fails?
                 curr = latest.get(user)

            # Helpers
            # Note: Analytics keys are normalized. 'user' from usernames list is normalized if from map keys.
            u_key = user.lower()
            
            def g(src, k): return src.get(u_key, {}).get(k, 0)
            def msg(src): return src.get(u_key, 0)
            
            row = {
                'Username': display_name,
                'Joined date': joined,
                'Role': role,
                'Total xp gained': curr.total_xp if curr else 0,
                'XP Gained 7d': g(gains_7d, 'xp'),
                'XP Gained 30d': g(gains_30d, 'xp'),
                'XP Gained 70d': g(gains_70d, 'xp'),
                'XP Gained 150d': g(gains_150d, 'xp'),
                'Total boss kills': curr.total_boss_kills if curr else 0,
                'Boss kills 7d': g(gains_7d, 'boss'),
                'Boss kills 30d': g(gains_30d, 'boss'),
                'Boss kills 70d': g(gains_70d, 'boss'),
                'Boss kills 150d': g(gains_150d, 'boss'),
                'Total Messages': msg(msgs_all),
                'Messages 7d': msg(msgs_7),
                'Messages 30d': msg(msgs_30),
                'Messages 70d': msg(msgs_70),
                'Messages 150d': msg(msgs_150),
            }
            data_list.append(row)
            
        # 7. Validate & Generate
        clean_data, warnings = DataValidator.validate_report_data(data_list)
        
        if clean_data:
            logger.info(f"Generating Excel for {len(clean_data)} rows...")
            reporter.generate(clean_data)
            
            # Drive Sync
            if Config.LOCAL_DRIVE_PATH and os.path.exists(Config.LOCAL_DRIVE_PATH):
                try:
                    target = os.path.join(Config.LOCAL_DRIVE_PATH, Config.OUTPUT_FILE_XLSX)
                    shutil.copy(Config.OUTPUT_FILE_XLSX, target)
                    logger.info(f"Synced to Drive: {target}")
                except Exception as e:
                    logger.error(f"Drive Sync Failed: {e}")
        else:
            logger.warning("No valid data to report.")
            
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
