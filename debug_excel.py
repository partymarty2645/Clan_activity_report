import sys
import os
import pandas as pd
sys.path.append(os.getcwd())

from reporting.excel import ExcelReporter
from reporting.styles import Theme

def test_excel_generation():
    print("Testing Excel Generation...")
    
    # Mock Data
    data = [
        {
            'Username': 'PlayerOne', 'Joined date': '2023-01-01', 'Role': 'Owner',
            'XP Gained 7d': 5000000, 'Total xp gained': 200000000,
            'Messages 30d': 150, 'Total Messages': 5000,
            'Boss kills 7d': 10, 'Total boss kills': 1000
        },
        {
            'Username': 'PlayerTwo', 'Joined date': '2023-02-01', 'Role': 'Member',
            'XP Gained 7d': 100000, 'Total xp gained': 50000000,
            'Messages 30d': 0, 'Total Messages': 10,
            'Boss kills 7d': 0, 'Total boss kills': 50
        }
    ]
    
    reporter = ExcelReporter()
    try:
        reporter.generate(data)
        print("Excel generation successful!")
    except Exception as e:
        print(f"FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_excel_generation()
