import shutil
import os
import datetime
import logging
from core.config import Config

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BACKUP_DIR = 'backups'

def backup_database():
    if not os.path.exists(Config.DB_FILE):
        logger.error(f"Database file {Config.DB_FILE} not found!")
        return

    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
        logger.info(f"Created backup directory: {BACKUP_DIR}")

    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = os.path.join(BACKUP_DIR, f'clan_data_{timestamp}.db')

    try:
        shutil.copy2(Config.DB_FILE, backup_file)
        logger.info(f"Database backed up successfully to: {backup_file}")
        
        # Cleanup: Keep only last 2 backups
        # Cleanup: Keep only last 2 backups (Strict Limit)
        # We check both naming conventions (clan_data_ and pre_run_)
        all_backups = sorted([
            os.path.join(BACKUP_DIR, f) 
            for f in os.listdir(BACKUP_DIR) 
            if f.endswith('.db')
        ], key=os.path.getmtime)
        
        while len(all_backups) > 2:
            oldest = all_backups.pop(0)
            try:
                os.remove(oldest)
                logger.info(f"Rotated backup (Deleted): {oldest}")
            except OSError as e:
                logger.warning(f"Failed to delete old backup {oldest}: {e}")
            except OSError as e:
                logger.warning(f"Failed to delete old backup {oldest}: {e}")
                
    except Exception as e:
        logger.error(f"Failed to backup database: {e}")

if __name__ == "__main__":
    backup_database()
