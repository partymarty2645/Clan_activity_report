
import os
import sys
import shutil
import asyncio
import logging
from datetime import datetime
import argparse

# Ensure we can import scripts
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from core.config import Config
from scripts.harvest_sqlite import run_sqlite_harvest
from database.connector import init_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("rebuild_database")

def backup_database():
    if not os.path.exists(Config.DB_FILE):
        return
        
    backup_dir = os.path.join(parent_dir, "backups")
    os.makedirs(backup_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(backup_dir, f"clan_data_BEFORE_REBUILD_{timestamp}.db")
    
    logger.info(f"Backing up existing database to {backup_path}...")
    try:
        shutil.copy2(Config.DB_FILE, backup_path)
    except Exception as e:
        logger.error(f"Backup failed: {e}")
        sys.exit(1)

def wipe_database():
    if os.path.exists(Config.DB_FILE):
        logger.warning(f"Deleting {Config.DB_FILE}...")
        try:
            os.remove(Config.DB_FILE)
            logger.info("Database deleted.")
        except Exception as e:
            logger.error(f"Deletion failed: {e}")
            sys.exit(1)

async def main():
    parser = argparse.ArgumentParser(description="Clean Database Rebuild")
    parser.add_argument("--force", action="store_true", help="Skip confirmation prompt")
    args = parser.parse_args()
    
    print("⚠️  WARNING: This will DELETE the existing database and fetch EVERYTHING from scratch.")
    print("   - Discord History: Will be fetched from 2025-02-14 (Founding Date)")
    print("   - WOM History: Will be fetched for ALL members (Deep Scan)")
    print("   - Duration: This may take SEVERAL HOURS.")
    
    if not args.force:
        response = input("\nAre you sure you want to proceed? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            print("Aborted.")
            return

    # 1. Backup
    backup_database()
    
    # 2. Wipe
    wipe_database()
    
    # 3. Init
    logger.info("Initializing Schema...")
    init_db()
    
    # 4. Deep Harvest
    logger.info("Starting Deep Harvest (Rebuild Phase 1)...")
    try:
        # We call the async function directly
        await run_sqlite_harvest()
    except Exception as e:
        logger.error(f"Harvest failed: {e}")
        return

    logger.info("Rebuild Complete! You may now run the report/export scripts.")
    # We could run them here, but keeping it decoupled is safer/more modular?
    # Or strict rebuild usually implies having a usable dashboard at end.
    # Let's run them.
    
    # Imports for report/export would be needed here or subprocess
    # subprocess is safer to avoid pollution
    import subprocess
    
    logger.info("Generating Report (Rebuild Phase 2)...")
    subprocess.run([sys.executable, "scripts/report_sqlite.py"], check=False)
    
    logger.info("Exporting Dashboard (Rebuild Phase 3)...")
    subprocess.run([sys.executable, "scripts/export_sqlite.py"], check=False)
    
    logger.info("✅ Full Rebuild Pipeline Finished Successfully.")

if __name__ == "__main__":
    asyncio.run(main())
