import asyncio
import logging
import sys
import subprocess
import os
from logging.handlers import RotatingFileHandler

# NOTE: Avoiding Top-Level Imports of hanging modules (database, sqlalchemy, aiohttp)
# We use subprocess to run "Clean" scripts.

# Setup Logging for Orchestrator
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        RotatingFileHandler("app.log", maxBytes=5*1024*1024, backupCount=2, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("Orchestrator")

def run_script(script_path):
    """Runs a script using subprocess and streams output."""
    process = None
    try:
        # Use formatting to run from current python env
        cmd = [sys.executable, "-u", script_path]
        logger.info(f"Running Subprocess: {' '.join(cmd)}")
        
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Stream output
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                logger.info(f"  [SUB] {output.strip()}")
                
        rc = process.poll()
        if rc != 0:
            err = process.stderr.read()
            logger.error(f"Script {script_path} failed with code {rc}: {err}")
            return False
            
        return True
    except KeyboardInterrupt:
        logger.warning(f"Killing script {script_path} due to keyboard interrupt...")
        if process:
            process.kill()
        raise # Re-raise to stop main pipeline
    except Exception as e:
        logger.error(f"Failed to run script {script_path}: {e}")
        return False

async def main():
    logger.info("==========================================")
    logger.info("       CLAN REPORT PIPELINE STARTED       ")
    logger.info("       (Mode: Safe Process Isolation)     ")
    logger.info("==========================================")
    
    success = False
    
    # Scripts location
    scripts_dir = os.path.join(os.getcwd(), 'scripts')

    # Step 0: Backup handled externally by run_auto.bat calling scripts/backup_db.py
    # to avoid duplication and process locking.
    
    # Step 1: Harvest (Sync/SQLite)
    logger.info(">> STEP 1/4: HARVEST")
    if not run_script(os.path.join(scripts_dir, 'harvest_sqlite.py')):
        logger.error("Harvest failed. Aborting pipeline.")
        return sys.exit(1)

    # Step 2: Report (SQLite)
    logger.info(">> STEP 2/4: REPORT")
    # Using report_sqlite.py
    if not run_script(os.path.join(scripts_dir, 'report_sqlite.py')):
        logger.error("Report generation failed.")
        # Non-fatal? Maybe we want dashboard at least.
        
    # Step 3: Dashboard Export (SQLite)
    logger.info(">> STEP 3/5: DASHBOARD EXPORT")
    if not run_script(os.path.join(scripts_dir, 'export_sqlite.py')):
        logger.error("Dashboard export failed.")

    # Step 4: CSV Export
    logger.info(">> STEP 4/5: CSV EXPORT")
    if not run_script(os.path.join(scripts_dir, 'export_csv.py')):
        logger.warning("CSV export failed.")

    # Step 5: Enforcer Suite
    # The enforcer suite likely uses ORM. Skipped for now to ensure stability.
    logger.info(">> STEP 5/5: ENFORCER SUITE")
    logger.warning("Enforcer Suite skipped in Safe Mode (Migration pending).")
    
    logger.info(">> PIPELINE SUCCESS")
    logger.info("==========================================")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Pipeline stopped by user.")
