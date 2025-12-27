import sys
import os
import logging

sys.path.append(os.getcwd())
from database.connector import SessionLocal
from database.models import ClanMember

# Setup minimal logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("DeleteGhosts")

def delete_ghosts():
    # Users confirmed 'Not Found on Hiscores'
    ghosts = [
        'anoobpure', 'ciaomano', 'drunkenduff', 'imp2k', 
        'kutthroat94', 'miikaielii', 'rolled1'
    ]
    
    session = SessionLocal()
    try:
        print(f"Deleting {len(ghosts)} confirmed ghost users...")
        
        deleted_count = 0
        for username in ghosts:
            member = session.query(ClanMember).filter(ClanMember.username == username).one_or_none()
            if member:
                session.delete(member)
                print(f"✅ Deleted: {username}")
                deleted_count += 1
            else:
                print(f"⚠️ Not Found in DB: {username}")
                
        session.commit()
        print(f"Deletion Complete. Removed {deleted_count} users.")
        
    except Exception as e:
        session.rollback()
        print(f"Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    delete_ghosts()
