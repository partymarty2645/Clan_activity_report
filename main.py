import asyncio
import logging
import sys
import traceback
from logging.handlers import RotatingFileHandler

# Import modules to run
# Import modules to run
from harvest import run_harvest
from report import run_report
from services.wom import wom_client
from dashboard_export import export_dashboard_json
from reporting.moderation import analyze_moderation
from reporting.enforcer import run_enforcer_suite

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

async def main():
    logger.info("==========================================")
    logger.info("       CLAN REPORT PIPELINE STARTED       ")
    logger.info("==========================================")
    
    success = False
    try:
        # Step 1: Harvest
        logger.info(">> STEP 1/4: HARVEST")
        await run_harvest(close_client=False)
        
        # Step 2: Report
        logger.info(">> STEP 2/4: REPORT")
        await run_report(close_client=False) # We close manually at very end
        
        # Step 3: Dashboard JSON export (optional visual dashboard)
        try:
            logger.info(">> STEP 3/4: DASHBOARD EXPORT")
            export_dashboard_json()
        except Exception as e:
            logger.warning(f"Dashboard export failed (non-fatal): {e}")

        # Step 4: Enforcer Suite
        try:
            logger.info(">> STEP 4/4: ENFORCER SUITE")
            await analyze_moderation(output_file="moderation_report.txt")
            await run_enforcer_suite()
            logger.info("   -> Enforcer Reports Generated.")
        except Exception as e:
             logger.error(f"Enforcer Suite failed (non-fatal): {e}")
        
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
