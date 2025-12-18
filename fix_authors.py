import logging
import re
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from database.models import DiscordMessage

# Config
DB_URL = "sqlite:///clan_data.db"
RELAY_BOT_NAME = "Osrs clanchat#0000"

# Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AuthorFix")

engine = create_engine(DB_URL)
SessionLocal = sessionmaker(bind=engine)

def fix_authors():
    session = SessionLocal()
    try:
        # Find all messages from the relay bot
        stmt = select(DiscordMessage).where(DiscordMessage.author_name == RELAY_BOT_NAME)
        messages = session.execute(stmt).scalars().all()
        
        logger.info(f"Found {len(messages)} messages from relay bot.")
        
        updated_count = 0
        regex = re.compile(r"\*\*(.+?)\*\*:")
        
        for msg in messages:
            content = msg.content or ""
            match = regex.search(content)
            if match:
                real_user = match.group(1).strip()
                # Update the author name
                # logger.info(f"Fixing: {msg.id} -> {real_user}")
                msg.author_name = real_user
                updated_count += 1
                
        session.commit()
        logger.info(f"Successfully updated {updated_count} messages.")
        
    except Exception as e:
        logger.error(f"Error: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    fix_authors()
