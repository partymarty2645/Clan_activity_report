import pandas as pd

def check():
    df = pd.read_excel("clan_report_summary_merged.xlsx", sheet_name='Clan Roster')
    row = df[df['Name'].astype(str).str.contains('kventiax', case=False, na=False)]
    
    if row.empty:
        print("❌ kventiax NOT FOUND in Excel")
    else:
        print("✅ kventiax FOUND")
        print(row[['Name', 'Total XP', 'Total Boss']].to_string())

if __name__ == "__main__":
    check()
