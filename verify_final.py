
import openpyxl
import os

filename = 'clan_report_summary_merged.xlsx'

print(f"Verifying {filename}...")
if not os.path.exists(filename):
    print("File does not exist!")
    exit(1)

try:
    wb = openpyxl.load_workbook(filename)
    print("Success: openpyxl loaded the file.")
    print("Sheet names:", wb.sheetnames)
except Exception as e:
    print(f"Verification failed: {e}")
    exit(1)
