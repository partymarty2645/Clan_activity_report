#!/usr/bin/env python3
"""
Database initialization script
Creates all tables if they don't exist.
"""
import os
import sys
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, DateTime, Float, Boolean, Text, ForeignKey

def initialize_database():
    """Initialize the database schema manually."""
    db_path = "clan_data.db"
    db_url = f"sqlite:///{db_path}"
    
    print(f"Initializing database: {db_path}")
    
    engine = create_engine(
        db_url, 
        connect_args={"check_same_thread": False}
    )
    
    metadata = MetaData()
    
    # Create clan_members table
    clan_members = Table('clan_members', metadata,
        Column('id', Integer, primary_key=True),
        Column('username', String(50), nullable=False, unique=True),
        Column('role', String(20)),
        Column('joined_at', DateTime),
        Column('last_updated', DateTime)
    )
    
    # Create wom_snapshots table  
    wom_snapshots = Table('wom_snapshots', metadata,
        Column('id', Integer, primary_key=True),
        Column('user_id', Integer, ForeignKey('clan_members.id')),
        Column('timestamp', DateTime, nullable=False),
        Column('total_xp', Integer, default=0),
        Column('total_boss_kills', Integer, default=0)
    )
    
    # Create discord_messages table
    discord_messages = Table('discord_messages', metadata,
        Column('id', Integer, primary_key=True),
        Column('user_id', Integer, ForeignKey('clan_members.id')),
        Column('created_at', DateTime, nullable=False),
        Column('content', Text)
    )
    
    # Create player_name_aliases table
    player_name_aliases = Table('player_name_aliases', metadata,
        Column('id', Integer, primary_key=True),
        Column('member_id', Integer, ForeignKey('clan_members.id')),
        Column('normalized_name', String(50), nullable=False),
        Column('canonical_name', String(50), nullable=False),
        Column('source', String(20)),
        Column('first_seen_at', DateTime),
        Column('last_seen_at', DateTime),
        Column('is_current', Boolean, default=False)
    )
    
    # Create all tables
    metadata.create_all(engine)
    
    print("✅ Database tables created successfully!")
    
    # List created tables
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"Created {len(tables)} tables:")
    for table in tables:
        print(f"  - {table}")

if __name__ == "__main__":
    initialize_database()