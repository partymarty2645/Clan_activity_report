import sys
import os
import requests
import logging

sys.path.append(os.getcwd())
from core.config import Config

# Setup minimal logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("Revive")

def revive_user():
    username = "00redrum00"
    logger.info(f"Attempting to REVIVE {username} via WOM Update...")
    
    url = f"https://api.wiseoldman.net/v2/players/{username}"
    
    try:
        # POST to update/create
        resp = requests.post(url)
        
        if resp.status_code == 200:
            print(f"✅ SUCCESS! User revived/updated.")
            print(resp.json())
        else:
            print(f"❌ FAILED to revive: {resp.status_code}")
            try:
                print(resp.json())
            except:
                print(resp.text)
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    revive_user()
