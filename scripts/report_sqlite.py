import sys
import os
import logging
import datetime
from datetime import timezone

# Ensure root path is in sys.path
sys.path.append(os.getcwd())

from reporting.excel import reporter
from core.config import Config
from core.usernames import UsernameNormalizer
from core.timestamps import TimestampHelper
from database.connector import SessionLocal
from core.analytics import AnalyticsService
from database.models import ClanMember

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("ReportSQLite")

def load_metadata(session, min_timestamps=None):
    """
    Loads member metadata (role, joined_at) using ORM.
    Enriches joined_at using min_timestamps fallback.
    """
    # Use ORM to fetch members
    members = session.query(ClanMember).all()
    
    metadata = {}
    for m in members:
        username = m.username
        role = m.role
        joined_dt = m.joined_at # datetime object from ORM

        # 2. Fallback to Min Snapshot
        if not joined_dt and min_timestamps:
            norm = UsernameNormalizer.normalize(username)
            if norm in min_timestamps:
                snap = min_timestamps[norm]
                # snap is WOMSnapshot object
                if snap.timestamp:
                    joined_dt = snap.timestamp
                    # Ensure UTC
                    if joined_dt.tzinfo is None:
                        joined_dt = joined_dt.replace(tzinfo=timezone.utc)

        # 3. Clamp to Clan Founding Date (Centralized in Config)
        if joined_dt:
            if joined_dt.tzinfo is None:
                joined_dt = joined_dt.replace(tzinfo=timezone.utc)
            
            if joined_dt < Config.CLAN_FOUNDING_DATE:
                joined_dt = Config.CLAN_FOUNDING_DATE
        
        metadata[UsernameNormalizer.normalize(username)] = {
            'username': username,
            'role': role,
            'joined_at': joined_dt.strftime('%Y-%m-%d') if joined_dt else None
        }
    return metadata

def run_report_sync():
    logger.info("Initializing analytics engine for report generation...", extra={'trace_id': 'REPORT'})
    
    db = SessionLocal()
    try:
        analytics = AnalyticsService(db)
        
        # Fetch min timestamps for metadata fallback
        min_ts = analytics.get_min_timestamps()
        metadata = load_metadata(db, min_ts)
        
        logger.info(f"Report Metadata: Loaded {len(metadata)} user profiles.")
        
        # ExcelReporter will use the passed analytics service
        reporter.generate(analytics, metadata=metadata)
        logger.info("Excel Report successfully generated.")
        
    except Exception as e:
        logger.error(f"Failed to generate report: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

    # --- Export to Drive using Utility ---
    # --- Export to Drive using Utility ---
    if Config.LOCAL_DRIVE_PATH:
        from core.drive import DriveExporter
        
        # Expert Full Report (Merged)
        target_name = Config.OUTPUT_FILE_XLSX 
        if os.path.exists(target_name):
            DriveExporter.export_file(target_name)
        else:
            logger.error(f"Could not find {target_name} to export!")

if __name__ == "__main__":
    run_report_sync()
