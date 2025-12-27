import pandas as pd

def check_revived():
    targets = [
        '00redrum00', 'bigbaosj', 'btgslaughter', 'ddsspeczz', 'lightblind', 
        'll05', 'llo6', 'pur3mtndck', 'rezthepker', 'smackachod3', 
        'thorrfinnnn', 'trejaco', 'wretchedseed', 'xleex', 'xstl314'
    ]
    
    try:
        df = pd.read_excel("clan_report_summary_merged.xlsx", sheet_name='Clan Roster')
        print(f"{'User':<15} | {'XP':<10} | {'Boss':<5} | {'Status'}")
        print("-" * 45)
        
        found_ct = 0
        nonzero_boss = 0
        
        for t in targets:
            row = df[df['Name'].astype(str).str.fullmatch(t, case=False, na=False)] # fullmatch strict
            # Actually, standard logic in excel is contains? No, logic is equality usually.
            # Let's use robust search.
            if row.empty:
                # Try contains
                row = df[df['Name'].astype(str).str.contains(t, case=False, na=False)]
            
            if row.empty:
                print(f"{t:<15} | {'MISSING':<10} | {'-':<5} | ❌")
            else:
                xp = row.iloc[0]['Total XP']
                boss = row.iloc[0]['Total Boss']
                print(f"{t:<15} | {xp:<10} | {boss:<5} | ✅")
                found_ct += 1
                if boss > 0:
                    nonzero_boss += 1
                    
        print("-" * 45)
        print(f"Summary: Found {found_ct}/{len(targets)}. Non-Zero Boss: {nonzero_boss}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_revived()
