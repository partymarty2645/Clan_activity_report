from sqlalchemy import Column, Integer, String, Text, Float, DateTime
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class DiscordMessage(Base):
    __tablename__ = 'discord_messages'

    id = Column(Integer, primary_key=True, autoincrement=False) # Discord IDs are big ints, provided by API
    author_id = Column(Integer)
    author_name = Column(String)
    content = Column(Text)
    channel_id = Column(Integer)
    channel_name = Column(String)
    guild_id = Column(Integer)
    guild_name = Column(String)
    created_at = Column(DateTime, index=True)

class WOMRecord(Base):
    __tablename__ = 'wom_records'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String)
    fetch_date = Column(DateTime)
    xp_30d = Column(Integer)
    msg_30d = Column(Integer)
    xp_150d = Column(Integer)
    msg_150d = Column(Integer)
    xp_custom = Column(Integer)
    msg_custom = Column(Integer)

class WOMSnapshot(Base):
    __tablename__ = 'wom_snapshots'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, index=True)
    timestamp = Column(DateTime, index=True)
    total_xp = Column(Integer)
    total_boss_kills = Column(Integer)
    ehp = Column(Float)
    ehb = Column(Float)
    raw_data = Column(Text)

class SkillSnapshot(Base):
    __tablename__ = 'skill_snapshots'

    id = Column(Integer, primary_key=True, autoincrement=True)
    snapshot_id = Column(Integer, index=True) # Foreign Key relationship handled manually or via simple join for speed
    skill_name = Column(String)
    xp = Column(Integer)
    level = Column(Integer)
    rank = Column(Integer)

class BossSnapshot(Base):
    __tablename__ = 'boss_snapshots'

    id = Column(Integer, primary_key=True, autoincrement=True)
    snapshot_id = Column(Integer, index=True)
    boss_name = Column(String)
    kills = Column(Integer)
    rank = Column(Integer)
