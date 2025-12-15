import asyncio
import logging
import sys
import traceback
from logging.handlers import RotatingFileHandler

# Import modules to run
from harvest import run_harvest
from report import run_report
from services.wom import wom_client

# Setup Logging for Orchestrator
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        RotatingFileHandler("app.log", maxBytes=5*1024*1024, backupCount=5, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("Orchestrator")

async def main():
    logger.info("==========================================")
    logger.info("       CLAN REPORT PIPELINE STARTED       ")
    logger.info("==========================================")
    
    success = False
    try:
        # Step 1: Harvest
        logger.info(">> STEP 1/2: HARVEST")
        await run_harvest(close_client=False)
        
        # Step 2: Report
        logger.info(">> STEP 2/2: REPORT")
        await run_report(close_client=False) # We close manually at very end
        
        success = True
        logger.info(">> PIPELINE SUCCESS")
        
    except Exception as e:
        logger.error(f"!! PIPELINE FAILED !! Error: {e}")
        logger.error(traceback.format_exc())
    finally:
        await wom_client.close()
        logger.info("==========================================")
        if hasattr(sys, 'exc_info') and sys.exc_info()[0]:
             logger.info("       PIPELINE FINISHED WITH ERRORS      ")
        else:
             logger.info("       PIPELINE FINISHED                  ")
        logger.info("==========================================")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Pipeline stopped by user.")
