from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from core.config import Config
from .models import Base

# DB_FILE is in root, so we need a relative path or absolute
# Config.DB_FILE is just 'clan_data.db'
# SQLAlchemy needs 'sqlite:///clan_data.db'

DB_URL = f"sqlite:///{Config.DB_FILE}"

# Use StaticPool for SQLite to maintain a single connection that's reused
# This prevents connection pool exhaustion and lock contention
engine = create_engine(
    DB_URL, 
    connect_args={
        "check_same_thread": False,
        "timeout": 30  # 30 second timeout for lock waits
    },
    poolclass=StaticPool,
    pool_pre_ping=True,  # Test connections before use
    echo=False
)
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
