
import sys
import os
import json
import logging
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, select, func

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connector import SessionLocal, init_db, engine
from database.models import WOMSnapshot, SkillSnapshot, BossSnapshot, Base

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("Migration")

def run_migration():
    logger.info("Starting Database Normalization Migration...")
    
    # 1. Create Tables
    Base.metadata.create_all(bind=engine)
    logger.info("Tables ensured.")
    
    session = SessionLocal()
    try:
        # 2. Check how many snapshots
        total = session.query(func.count(WOMSnapshot.id)).scalar()
        logger.info(f"Found {total} snapshots to process.")
        
        # 3. Check if we already have data (idempotency check)
        existing_skills = session.query(func.count(SkillSnapshot.id)).scalar()
        if existing_skills > 0:
            logger.warning(f"SkillSnapshot table already has {existing_skills} rows.")
            logger.warning("continuing might duplicate data. Please clear table if you want full re-run.")
            # return # For now, let's just proceed or maybe we should query which IDs are done?
            # Ideally we check max snapshot_id in SkillSnapshot and start from there.
            max_done = session.query(func.max(SkillSnapshot.snapshot_id)).scalar() or 0
            logger.info(f"Resuming from snapshot_id > {max_done}")
        else:
            max_done = 0

        # 4. Iterate and Insert in Batches
        BATCH_SIZE = 1000
        count = 0 
        skills_buffer = []
        bosses_buffer = []
        
        while True:
            # Fetch batch based on ID > max_done
            current_batch = session.query(WOMSnapshot).filter(WOMSnapshot.id > max_done).order_by(WOMSnapshot.id).limit(BATCH_SIZE).all()
            
            if not current_batch:
                break
            
            for snap in current_batch:
                max_done = snap.id
                if not snap.raw_data or len(snap.raw_data) < 5 or snap.raw_data == 'None':
                    continue
                
            try:
                data = json.loads(snap.raw_data)
                
                # Skills
                skills = data.get('data', {}).get('skills', {})
                for s_name, s_data in skills.items():
                    skills_buffer.append(SkillSnapshot(
                        snapshot_id=snap.id,
                        skill_name=s_name,
                        xp=s_data.get('experience', 0),
                        level=s_data.get('level', 1),
                        rank=s_data.get('rank', -1)
                    ))
                
                # Bosses
                bosses = data.get('data', {}).get('bosses', {})
                for b_name, b_data in bosses.items():
                    kills = b_data.get('kills', -1)
                    if kills > 0: # Optimization: Don't store 0kc? Or maybe we should for rank tracking? 
                        # Storing 0 is wasteful. Only store > -1 or > 0?
                        # Report logic checks for > 0 usually.
                        # Let's store > -1 to be safe, but typically 0 is implicit.
                        # Let's store > 0 to save space.
                         bosses_buffer.append(BossSnapshot(
                            snapshot_id=snap.id,
                            boss_name=b_name,
                            kills=kills,
                            rank=b_data.get('rank', -1)
                        ))
                
                count += 1
                
                if count % BATCH_SIZE == 0:
                    session.bulk_save_objects(skills_buffer)
                    session.bulk_save_objects(bosses_buffer)
                    session.commit()
                    skills_buffer = []
                    bosses_buffer = []
                    logger.info(f"Processed {count} snapshots...")

            except Exception as e:
                logger.error(f"Error parsing snapshot {snap.id}: {e}")
                
        # Final batch
        if skills_buffer or bosses_buffer:
            session.bulk_save_objects(skills_buffer)
            session.bulk_save_objects(bosses_buffer)
            session.commit()
            
        logger.info(f"Migration Complete! Processed {count} new snapshots.")
        
    except Exception as e:
        logger.error(f"Migration Failed: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    run_migration()
