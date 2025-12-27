import sys
import os
sys.path.append(os.getcwd())
from database.connector import SessionLocal
from database.models import ClanMember

def delete_final_two():
    ghosts = ['cervixthumpr', 'sulkypeen']
    session = SessionLocal()
    try:
        print(f"Deleting verified ghosts: {ghosts}...")
        for u in ghosts:
            m = session.query(ClanMember).filter(ClanMember.username == u).one_or_none()
            if m:
                session.delete(m)
                print(f"✅ Deleted {u}")
            else:
                print(f"⚠️ {u} not found in DB")
        session.commit()
    finally:
        session.close()

if __name__ == "__main__":
    delete_final_two()
