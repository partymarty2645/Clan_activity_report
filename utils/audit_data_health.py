
import sys
import os
import logging
# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connector import SessionLocal
from database.models import WOMSnapshot
from sqlalchemy import func, text

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("Audit")

def audit():
    session = SessionLocal()
    try:
        logger.info("--- Database Health Audit ---")
        
        # Total rows
        total = session.query(func.count(WOMSnapshot.id)).scalar()
        logger.info(f"Total Snapshots: {total}")
        
        if total == 0:
            return

        # Empty/Null raw_data
        # Note: checking length might be slow on huge DB, but acceptable for 300MB
        empty = session.query(func.count(WOMSnapshot.id)).filter(
            (WOMSnapshot.raw_data == None) | (WOMSnapshot.raw_data == '')
        ).scalar()
        
        logger.info(f"Empty/Null Raw Data: {empty} ({empty/total*100:.1f}%)")
        
        # 'None' string (common artifact)
        none_str = session.query(func.count(WOMSnapshot.id)).filter(WOMSnapshot.raw_data == 'None').scalar()
        logger.info(f"'None' String Artifacts: {none_str} ({none_str/total*100:.1f}%)")
        
        # Likely Valid (Starts with '{')
        valid_start = session.query(func.count(WOMSnapshot.id)).filter(WOMSnapshot.raw_data.like('{%')).scalar()
        logger.info(f"Likely Valid JSON (starts with {{): {valid_start} ({valid_start/total*100:.1f}%)")
        
        # Size on disk
        db_path = "e:\\Clan_activity_report\\clan_data.db"
        if os.path.exists(db_path):
             size_mb = os.path.getsize(db_path) / (1024*1024)
             logger.info(f"DB Size: {size_mb:.2f} MB")

    except Exception as e:
        logger.error(f"Audit failed: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    audit()
