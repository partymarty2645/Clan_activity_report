
import pandas as pd
import os
from reporting.excel import reporter
from reporting.styles import Theme

def test_generation():
    print("Testing Excel Generation...")
    
    # Dummy Data
    data = [
        {
            'Username': 'PlayerOne',
            'Joined date': '2023-01-01',
            'Role': 'Owner',
            'XP Gained 7d': 5000000,
            'XP Gained 30d': 20000000,
            'Total xp gained': 150000000,
            'Messages 7d': 100,
            'Total Messages': 5000,
            'Boss kills 7d': 50,
            'Total boss kills': 1200
        },
        {
            'Username': 'PlayerTwo',
            'Joined date': '2023-02-01',
            'Role': 'Member',
            'XP Gained 7d': 0,
            'XP Gained 30d': 1000,
            'Total xp gained': 50000,
            'Messages 7d': 0,
            'Total Messages': 10,
            'Boss kills 7d': 0,
            'Total boss kills': 5
        }
    ]
    
    try:
        reporter.generate(data)
        print("Generation call finished.")
    except Exception as e:
        print(f"Generation failed: {e}")
        return

    print("Verifying file integrity with openpyxl...")
    try:
        import openpyxl
        wb = openpyxl.load_workbook('clan_report_summary_merged.xlsx')
        print("Success: openpyxl loaded the file.")
    except Exception as e:
        print(f"Verification failed: {e}")

if __name__ == "__main__":
    test_generation()
