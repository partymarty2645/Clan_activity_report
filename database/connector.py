from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from core.config import Config
from .models import Base

# DB_FILE is in root, so we need a relative path or absolute
# Config.DB_FILE is just 'clan_data.db'
# SQLAlchemy needs 'sqlite:///clan_data.db'

DB_URL = f"sqlite:///{Config.DB_FILE}"

engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Initializes the database schema (creates tables if missing)."""
    Base.metadata.create_all(bind=engine)

def get_db():
    """Dependency: yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
