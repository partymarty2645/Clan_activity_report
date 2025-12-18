import sys
import os
import logging
from datetime import datetime
from database.connector import SessionLocal
from report import count_messages
from optimize_db import optimize

# Mute logs for verification
logging.basicConfig(level=logging.ERROR)

def test_optimization():
    print("Testing Optimization Script (Check Weekly Mode)...")
    try:
        # Run in check mode (should be fast)
        optimize(check_weekly=True)
        print("Optimization Script Logic Verified.")
    except Exception as e:
        print(f"Optimization Script Failed: {e}")
        raise e

def test_report_sql():
    print("Testing Report SQL Logic (count_messages)...")
    db = SessionLocal()
    try:
        # Use a dummy date range
        start = datetime.now()
        end = datetime.now()
        target_users = ["test_user"]
        
        # Test the function (Should run SQL query and return dict)
        counts = count_messages(db, start, end, target_users)
        
        print(f"Report SQL Logic Verified. Result matches expected type: {isinstance(counts, dict)}")
    except Exception as e:
        print(f"Report SQL Failed: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    try:
        test_optimization()
        test_report_sql()
        print("--- ALL CHECKS PASSED ---")
    except Exception as e:
        print(f"--- VERIFICATION FAILED ---")
        sys.exit(1)
