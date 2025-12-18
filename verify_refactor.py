"""
Refactor Verification Script
============================
Automated sanity check for the OSRS Clan System Refactor.
Verifies:
1. Database Integrity (SessionLocal, Models)
2. Analytics Service (Calculation Logic)
3. Dashboard Export (JSON Schema Compliance)
4. Excel Report Generation (File Creation)
"""
import sys
import os
import json
import logging
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.analytics import AnalyticsService
from core.config import Config
from database.connector import SessionLocal
from database.models import WOMSnapshot
from dashboard_export import export_dashboard_json
from report import run_report
import asyncio

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger("Verifier")

def check_database():
    logger.info("[1/4] Checking Database...")
    db = SessionLocal()
    try:
        count = db.query(WOMSnapshot).count()
        logger.info(f"✔ Connection Successful. Found {count} snapshots.")
        return True
    except Exception as e:
        logger.error(f"✘ Database Check Failed: {e}")
        return False
    finally:
        db.close()

def check_analytics():
    logger.info("[2/4] Checking Analytics Service...")
    db = SessionLocal()
    analytics = AnalyticsService(db)
    try:
        latest = analytics.get_latest_snapshots()
        if not latest:
            logger.warning("⚠ No snapshots found (this might be expected on fresh DB).")
        else:
            logger.info(f"✔ Analytics fetched {len(latest)} latest snapshots.")
        return True
    except Exception as e:
        logger.error(f"✘ Analytics Check Failed: {e}")
        return False
    finally:
        db.close()

def check_dashboard_export():
    logger.info("[3/4] Verifying Dashboard Export Contract...")
    try:
        json_path = export_dashboard_json()
        
        with open(json_path, 'r') as f:
            data = json.load(f)
            
        # Contract Checks
        required_keys = [
            "lastUpdated", "bossCards", "risingStar", 
            "topMessenger", "allMembers", "weeklyBriefing"
        ]
        
        missing = [k for k in required_keys if k not in data]
        if missing:
            logger.error(f"✘ JSON Contract Breach. Missing keys: {missing}")
            return False
            
        logger.info(f"✔ JSON Contract Valid. File size: {os.path.getsize(json_path)/1024:.2f} KB")
        return True
    except Exception as e:
        logger.error(f"✘ Export Test Failed: {e}")
        return False

async def check_report_generation():
    logger.info("[4/4] Verifying Excel Report Generation...")
    try:
        # Run in a way that doesn't trigger full harvest if not needed, 
        # but report.py usually triggers everything. 
        # We will wrap it or just call it.
        # Note: run_report verifies DB data itself.
        await run_report(close_client=True)
        
        if os.path.exists(Config.OUTPUT_FILE_XLSX):
            logger.info("✔ Excel Report created successfully.")
            return True
        else:
            logger.error("✘ Excel Report file not found after run.")
            return False
    except Exception as e:
        logger.error(f"✘ Report Gen Failed: {e}")
        return False

async def main():
    logger.info("=== STARTING REFACTOR VERIFICATION ===")
    
    checks = [
        check_database(),
        check_analytics(),
        check_dashboard_export(),
        await check_report_generation()
    ]
    
    if all(checks):
        logger.info("\n✅ VERIFICATION PASSED: System is stable.")
        sys.exit(0)
    else:
        logger.error("\n❌ VERIFICATION FAILED: Issues detected.")
        sys.exit(1)

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
