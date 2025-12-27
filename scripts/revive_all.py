import sys
import os
import requests
import time
import logging

sys.path.append(os.getcwd())
from core.config import Config

# Setup minimal logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("ReviveBatch")

def revive_batch():
    problem_users = [
        '00redrum00', 'anoobpure', 'bigbaosj', 'btgslaughter', 'ciaomano', 
        'ddsspeczz', 'drunkenduff', 'imp2k', 'kutthroat94', 'lightblind', 
        'll05', 'llo6', 'miikaielii', 'pur3mtndck', 'rezthepker', 
        'rolled1', 'smackachod3', 'thorrfinnnn', 'trejaco', 'wretchedseed', 
        'xleex', 'xstl314'
    ]
    
    print(f"Batch Reviving {len(problem_users)} users...")
    
    success_count = 0
    fail_count = 0
    
    for i, user in enumerate(problem_users, 1):
        url = f"https://api.wiseoldman.net/v2/players/{user}"
        print(f"[{i}/{len(problem_users)}] Reviving {user}...", end=" ", flush=True)
        
        try:
            resp = requests.post(url)
            if resp.status_code == 200:
                print("✅ OK")
                success_count += 1
            elif resp.status_code == 400:
                 # Check if "Player not found"
                 print(f"❌ '{user}' Not Found on Hiscores")
                 fail_count += 1
            else:
                print(f"⚠️ Status {resp.status_code}")
                fail_count += 1
        except Exception as e:
            print(f"⚠️ Error: {e}")
            fail_count += 1
            
        # Polite delay
        time.sleep(1.0)
        
    print(f"\nRevival Complete. Success: {success_count}, Failed: {fail_count}")
    print("Please run Harvest now to fetch their data.")

if __name__ == "__main__":
    revive_batch()
