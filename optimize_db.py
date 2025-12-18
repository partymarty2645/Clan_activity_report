import sqlite3
import time
import os
import argparse
import logging
from datetime import datetime, timedelta

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger("DB_Optimizer")

DB_PATH = 'clan_data.db'
LOG_FILE = 'db_maintenance.log'

def get_last_run_time():
    if not os.path.exists(LOG_FILE):
        return None
    try:
        with open(LOG_FILE, 'r') as f:
            last_line = f.readlines()[-1]
            # Format: 2023-10-27 10:00:00 - Optimization Complete.
            date_str = last_line.split(' - ')[0]
            return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
    except Exception:
        return None

def log_completion():
    with open(LOG_FILE, 'a') as f:
        f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Optimization Complete.\n")

def optimize(check_weekly=False):
    if check_weekly:
        last_run = get_last_run_time()
        if last_run and (datetime.now() - last_run) < timedelta(days=7):
            logger.info("Skipping optimization: Last run was less than 7 days ago.")
            return

    logger.info(f"Connecting to {DB_PATH}...")
    try:
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
        
        # 0. WAL Mode (Best practice for concurrency)
        cur.execute("PRAGMA journal_mode=WAL;")
        mode = cur.fetchone()[0]
        logger.info(f"Journal Mode set to: {mode}")

        # 1. INDICES
        logger.info("--- Creating Indices ---")
        
        # WOM Snapshots
        cur.execute("CREATE INDEX IF NOT EXISTS idx_wom_snapshots_username_timestamp ON wom_snapshots (username, timestamp)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_wom_snapshots_timestamp ON wom_snapshots (timestamp)")
        
        # Discord Messages
        cur.execute("CREATE INDEX IF NOT EXISTS idx_discord_messages_created ON discord_messages (created_at)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_discord_messages_author ON discord_messages (author_name)")
        
        con.commit()
        
        # 2. ANALYZE
        logger.info("--- Running ANALYZE ---")
        start = time.time()
        cur.execute("ANALYZE")
        logger.info(f"Analyze complete in {time.time() - start:.2f}s")
        
        # 3. VACUUM INTO
        logger.info("--- Running VACUUM INTO 'optimized.db' (Memory Safe) ---")
        start = time.time()
        
        if os.path.exists('optimized.db'):
            os.remove('optimized.db')
            
        con.commit()
        cur.execute("PRAGMA cache_size = -20000") 
        
        try:
            cur.execute("VACUUM INTO 'optimized.db'")
            success = True
        except Exception as e:
            logger.error(f"VACUUM INTO failed: {e}")
            success = False
            
        con.close()
        
        if success:
            logger.info(f"Vacuum complete in {time.time() - start:.2f}s")
            logger.info("Swapping database files...")
            try:
                if os.path.exists('clan_data.db.bak'):
                    os.remove('clan_data.db.bak')
                    
                os.rename('clan_data.db', 'clan_data.db.bak')
                os.rename('optimized.db', 'clan_data.db')
                logger.info("Swap successful. Original DB backed up to 'clan_data.db.bak'.")
                
                # Log success for weekly check
                log_completion()
                
            except Exception as e:
                logger.error(f"Error swapping files: {e}")
                logger.info("The optimized DB is at 'optimized.db'.")
                
        logger.info("Optimization Complete.")
        
    except Exception as e:
        logger.error(f"Optimization failed: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-weekly", action="store_true", help="Only run if 7 days have passed since last run")
    args = parser.parse_args()
    
    optimize(check_weekly=args.check_weekly)
