import shutil
import os
import datetime
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_FILE = 'clan_data.db'
BACKUP_DIR = 'backups'

def backup_database():
    if not os.path.exists(DB_FILE):
        logger.error(f"Database file {DB_FILE} not found!")
        return

    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
        logger.info(f"Created backup directory: {BACKUP_DIR}")

    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = os.path.join(BACKUP_DIR, f'clan_data_{timestamp}.db')

    try:
        shutil.copy2(DB_FILE, backup_file)
        logger.info(f"Database backed up successfully to: {backup_file}")
        
        # Cleanup: Keep only last 2 backups
        backups = sorted([
            os.path.join(BACKUP_DIR, f) 
            for f in os.listdir(BACKUP_DIR) 
            if f.startswith('clan_data_') and f.endswith('.db')
        ], key=os.path.getmtime)
        
        while len(backups) > 2:
            oldest = backups.pop(0)
            try:
                os.remove(oldest)
                logger.info(f"Deleted old backup: {oldest}")
            except OSError as e:
                logger.warning(f"Failed to delete old backup {oldest}: {e}")
                
    except Exception as e:
        logger.error(f"Failed to backup database: {e}")

if __name__ == "__main__":
    backup_database()
