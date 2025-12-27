import sys
import os
import requests
import logging

sys.path.append(os.getcwd())
from database.connector import SessionLocal
from database.models import ClanMember
from core.config import Config

# Setup minimal logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("RestoreUser")

def check_and_restore():
    variations = [
        "A NoobPure", 
        "A Noob Pure", 
        "anoobpure", 
        "a noobpure",
        "A_NoobPure"
    ]
    
    print("--- Checking Variations on WOM ---")
    valid_name = None
    
    for name in variations:
        url = f"https://api.wiseoldman.net/v2/players/{name}"
        try:
            # Check if exists
            resp = requests.get(url)
            if resp.status_code == 200:
                print(f"✅ FOUND: '{name}'")
                valid_name = resp.json().get('username') # Get canonical name
                print(f"   Canonical: {valid_name}")
                break
            else:
                 print(f"❌ '{name}': {resp.status_code}")
                 
                 # Try forcing update if 404?
                 if resp.status_code == 404:
                     print(f"   Attempting update force for '{name}'...")
                     up_resp = requests.post(url)
                     if up_resp.status_code == 200:
                         print(f"   ✅ REVIVED: '{name}'")
                         valid_name = up_resp.json().get('username')
                         break
                     else:
                         print(f"   ❌ Update failed: {up_resp.status_code} - {up_resp.text}")
                         
        except Exception as e:
            print(f"Error checking {name}: {e}")
            
    if valid_name:
        print(f"\n--- Restoring '{valid_name}' to Database ---")
        session = SessionLocal()
        try:
            # Check if exists (maybe under different case)
            existing = session.query(ClanMember).filter(ClanMember.username == valid_name).one_or_none()
            if existing:
                print(f"⚠️ User '{valid_name}' already exists in DB! (ID: {existing.id})")
            else:
                new_member = ClanMember(
                    username=valid_name, 
                    role='Member', 
                    joined_at=None # Metadata will fix this or fallback
                )
                session.add(new_member)
                session.commit()
                print(f"✅ Successfully inserted '{valid_name}' into ClanMember table.")
                
                # Optionally run harvest for this user?
                # For now let's just restore DB entry.
                
        except Exception as e:
            session.rollback()
            print(f"DB Error: {e}")
        finally:
            session.close()
    else:
        print("\n❌ Could not find ANY valid variation. User might be banned or name changed without tracking.")

if __name__ == "__main__":
    check_and_restore()
