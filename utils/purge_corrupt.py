
import sys
import os
import logging
# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connector import SessionLocal, engine
from database.models import WOMSnapshot
from sqlalchemy import text

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("Purge")

def purge():
    logger.info("Starting Smart Purge...")
    session = SessionLocal()
    try:
        # 1. Delete Rows
        # Where raw_data is null OR empty string OR 'None'
        logger.info("Deleting corrupt rows...")
        
        # Using raw SQL for speed and textual representation consistency
        stmt = text("""
            DELETE FROM wom_snapshots 
            WHERE raw_data IS NULL 
            OR raw_data = '' 
            OR raw_data = 'None'
            OR length(raw_data) < 10
        """)
        
        result = session.execute(stmt)
        session.commit()
        deleted = result.rowcount
        logger.info(f"Deleted {deleted} rows.")
        
        # 2. VACUUM
        logger.info("Running VACUUM to reclaim space...")
        # Vacuum cannot run inside a transaction block in some drivers, 
        # but with SQLAlchemy execute it might work if autocommit or outside session.
        # SQLite VACUUM is a standalone command.
        
        # We need a raw connection for VACUUM usually
        with engine.connect() as conn:
            # conn.execute(text("VACUUM")) # Might fail if transaction active
             conn.execution_options(isolation_level="AUTOCOMMIT").execute(text("VACUUM"))
             
        logger.info("VACUUM Complete.")
        
    except Exception as e:
        logger.error(f"Purge failed: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    purge()
