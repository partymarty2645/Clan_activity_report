from sqlalchemy import Column, Integer, String, Text, Float, DateTime
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class DiscordMessage(Base):
    __tablename__ = 'discord_messages'

    id = Column(Integer, primary_key=True, autoincrement=False) # Discord IDs are big ints, provided by API
    user_id = Column(Integer, index=True)  # FK to clan_members.id
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
    user_id = Column(Integer, index=True)  # FK to clan_members.id
    username = Column(String, index=True)  # Keep for backward compatibility
    timestamp = Column(DateTime, index=True)
    total_xp = Column(Integer)
    total_boss_kills = Column(Integer)
    ehp = Column(Float)
    ehb = Column(Float)
    raw_data = Column(Text)

class ClanMember(Base):
    __tablename__ = 'clan_members'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, unique=True, nullable=False, index=True)
    role = Column(String)
    joined_at = Column(DateTime)
    last_updated = Column(DateTime)


class BossSnapshot(Base):
    __tablename__ = 'boss_snapshots'

    id = Column(Integer, primary_key=True, autoincrement=True)
    wom_snapshot_id = Column(Integer, index=True)  # FK to wom_snapshots.id
    snapshot_id = Column(Integer, index=True)  # Keep for backward compatibility (same as wom_snapshot_id)
    boss_name = Column(String, index=True)
    kills = Column(Integer)
    rank = Column(Integer)
