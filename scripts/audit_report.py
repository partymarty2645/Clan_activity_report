import pandas as pd
import os
from core.config import Config

def audit_excel_report():
    file_path = "clan_report_summary_merged.xlsx"
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return

    print(f"🔍 Auditing {file_path}...\n")
    
    try:
        df = pd.read_excel(file_path, sheet_name='Clan Roster')
    except Exception as e:
        print(f"❌ Failed to read Excel: {e}")
        return

    # Columns of interest
    col_name = 'Name'
    col_joined = 'Joined'
    col_total_xp = 'Total XP'
    col_total_boss = 'Total Boss'

    issues = []
    
    from core.usernames import UsernameNormalizer

    # 1. Duplicate Names (Normalized check)
    # Create a temporary normalized column for checking
    df['normalized_name'] = df[col_name].apply(lambda x: UsernameNormalizer.normalize(str(x)) if pd.notna(x) else '')
    
    # Check for normalized duplicates (e.g. "Noob Man" vs "noob man")
    dupe_mask = df.duplicated(subset=['normalized_name'], keep=False)
    duplicates = df[dupe_mask]
    
    if not duplicates.empty:
        # Group by normalized name to show the conflicting variations
        conflict_groups = duplicates.groupby('normalized_name')[col_name].apply(list).tolist()
        for group in conflict_groups:
             if len(set(group)) > 1:
                 # Real conflict (different strings)
                 issues.append(f"⚠️  Ambiguous Duplicate (Normalized Match): {group}")
             else:
                 # Exact duplicate
                 issues.append(f"⚠️  Exact Duplicate Username: {group[0]}")

    # Iterate rows for granular checks
    batch_size = 25
    batch_issues = []
    
    total_rows = len(df)
    print(f"Total Rows: {total_rows}\n")

    for index, row in df.iterrows():
        r_num = index + 1
        name = row.get(col_name, 'Unknown')
        joined = row.get(col_joined, 'N/A')
        xp = row.get(col_total_xp, 0)
        boss = row.get(col_total_boss, 0)
        
        row_mistakes = []

        # Check Joined
        if pd.isna(joined) or joined == 'N/A' or str(joined).strip() == '':
            row_mistakes.append(f"Joined Date is '{joined}'")
        
        # Check XP (Active member should have XP)
        if xp == 0:
            row_mistakes.append("Total XP is 0")
            
        # Check Name
        if pd.isna(name) or str(name).strip() == '':
             row_mistakes.append("Username is Empty")

        if row_mistakes:
            batch_issues.append(f"Row {r_num} [{name}]: {', '.join(row_mistakes)}")

        # Print Batch
        if r_num % batch_size == 0 or r_num == total_rows:
            if batch_issues:
                print(f"--- Batch {r_num-batch_size+1} to {r_num} ---")
                for issue in batch_issues:
                    print(issue)
                print("")
                batch_issues = [] # Reset for next batch

    if not issues and not batch_issues: # Check overall issues logic again
        # The batch_issues are printed in loop. 
        # Check if we had any issues at all? capture a global flag.
        pass

    print("✅ Audit Complete.")

if __name__ == "__main__":
    audit_excel_report()
