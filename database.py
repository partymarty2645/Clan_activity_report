import sqlite3
import os
from datetime import datetime

DB_FILE = 'clan_data.db'

def get_connection():
    """Returns a connection to the SQLite database."""
    return sqlite3.connect(DB_FILE)

def init_db():
    """Initializes the database schema."""
    conn = get_connection()
    c = conn.cursor()
    
    # 1. Discord Messages Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS discord_messages (
            id INTEGER PRIMARY KEY,
            author_id INTEGER,
            author_name TEXT,
            content TEXT,
            channel_id INTEGER,
            channel_name TEXT,
            guild_id INTEGER,
            guild_name TEXT,
            created_at TIMESTAMP
        )
    ''')
    
    # Indexes on created_at and author_name for fast range/user queries
    c.execute('CREATE INDEX IF NOT EXISTS idx_discord_created_at ON discord_messages(created_at)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_discord_author ON discord_messages(author_name)')
    
    # 2. WOM Records Table (Snapshots of run data)
    c.execute('''
        CREATE TABLE IF NOT EXISTS wom_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            fetch_date TIMESTAMP,
            xp_30d INTEGER,
            msg_30d INTEGER,
            xp_150d INTEGER,
            msg_150d INTEGER,
            xp_custom INTEGER,
            msg_custom INTEGER
        )
    ''')
    
    # Indexes for WOM snapshots (user lookups and time-based delta calculations)
    c.execute('CREATE INDEX IF NOT EXISTS idx_wom_snapshots_user ON wom_snapshots(username)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_wom_snapshots_user_time ON wom_snapshots(username, timestamp DESC)')
    
    # 3. WOM Snapshots Table (Full Stats History)
    c.execute('''
        CREATE TABLE IF NOT EXISTS wom_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            timestamp TIMESTAMP,
            total_xp INTEGER,
            total_boss_kills INTEGER,
            ehp REAL,
            ehb REAL,
            raw_data TEXT
        )
    ''')
    
    # Index for fast lookups
    c.execute('CREATE INDEX IF NOT EXISTS idx_wom_snapshots_user_time ON wom_snapshots(username, timestamp)')

    conn.commit()
    conn.close()
    print(f"Database initialized at {DB_FILE}")

def insert_messages(messages):
    """
    Inserts a list of message dicts into the database.
    Ignores duplicates based on ID.
    Returns: (inserted_count, skipped_count)
    """
    if not messages:
        return (0, 0)
        
    conn = get_connection()
    c = conn.cursor()
    
    # Prepare data for executemany
    data = []
    for msg in messages:
        data.append((
            msg['id'],
            msg.get('author_id'),
            msg.get('author_name'),
            msg.get('content'),
            msg.get('channel_id'),
            msg.get('channel_name'),
            msg.get('guild_id'),
            msg.get('guild_name'),
            msg.get('created_at')
        ))
    
    try:
        c.executemany('''
            INSERT OR IGNORE INTO discord_messages 
            (id, author_id, author_name, content, channel_id, channel_name, guild_id, guild_name, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', data)
        
        conn.commit()
        inserted = c.rowcount
        skipped = len(data) - inserted
        conn.close()
        return (inserted, skipped)
        
    except Exception as e:
        print(f"Error inserting messages: {e}")
        conn.close()
        return (0, 0)

def get_messages_in_range(start_dt, end_dt):
    """
    Yields messages within the given datetime range one by one.
    Optimized to select only used columns.
    """
    conn = get_connection()
    conn.row_factory = sqlite3.Row # Access columns by name
    c = conn.cursor()
    
    # Ensure ISO format strings for SQLite comparison
    start_iso = start_dt.isoformat()
    end_iso = end_dt.isoformat()
    
    try:
        # Only select columns actually used in main.py
        c.execute('''
            SELECT content, author_name FROM discord_messages 
            WHERE created_at >= ? AND created_at <= ?
        ''', (start_iso, end_iso))
        
        for row in c:
            yield row
    finally:
        conn.close()

def get_latest_message_time():
    """Returns the timestamp of the most recent message."""
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT MAX(created_at) FROM discord_messages')
    result = c.fetchone()[0]
    conn.close()
    return result

def get_earliest_message_time():
    """Returns the timestamp of the oldest message."""
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT MIN(created_at) FROM discord_messages')
    result = c.fetchone()[0]
    conn.close()
    return result

def insert_wom_snapshot(records):
    """
    Inserts a list of WOM record dicts into the database.
    Each record represents one user's stats for this run.
    """
    conn = get_connection()
    c = conn.cursor()
    
    fetch_date = datetime.now().isoformat()
    
    count = 0
    for r in records:
        try:
            c.execute('''
                INSERT INTO wom_records 
                (username, fetch_date, xp_30d, msg_30d, xp_150d, msg_150d, xp_custom, msg_custom)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                r.get('Username'),
                fetch_date,
                r.get('XP Gained (30d)'),
                r.get('Messages (30d)'),
                r.get('XP Gained (150d)'),
                r.get('Messages (150d)'),
                r.get('Total XP (Feb-Dec)'),
                r.get('Total Messages (Feb-Dec)')
            ))
            count += 1
        except Exception as e:
            print(f"Error inserting WOM record: {e}")
            
    conn.commit()
    conn.close()
    print(f"Saved {count} WOM records to database snapshot.")

def insert_wom_snapshot_full(data):
    """
    Inserts a full snapshot of a player's stats into wom_snapshots.
    data format: (username, total_xp, total_boss_kills, ehp, ehb, raw_json_str)
    """
    conn = get_connection()
    c = conn.cursor()
    
    timestamp = datetime.now().isoformat()
    
    try:
        c.execute('''
            INSERT INTO wom_snapshots (username, timestamp, total_xp, total_boss_kills, ehp, ehb, raw_data)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (data[0], timestamp, data[1], data[2], data[3], data[4], data[5]))
        conn.commit()
    except Exception as e:
        print(f"Error inserting WOM full snapshot: {e}")
    finally:
        conn.close()

def get_snapshot_before(username, target_date):
    """
    Finds the latest snapshot for a user that is ON or BEFORE target_date.
    Returns: (timestamp, total_xp, total_boss_kills, ehp, ehb, raw_data) or None
    """
    conn = get_connection()
    c = conn.cursor()
    
    target_iso = target_date.isoformat()
    
    try:
        c.execute('''
            SELECT timestamp, total_xp, total_boss_kills, ehp, ehb, raw_data 
            FROM wom_snapshots 
            WHERE username = ? AND timestamp <= ?
            ORDER BY timestamp DESC
            LIMIT 1
        ''', (username, target_iso))
        
        return c.fetchone()
    except Exception as e:
        print(f"Error fetching snapshot: {e}")
        return None
    finally:
        conn.close()

def get_todays_snapshot(username):
    """
    Checks if a snapshot for the given user already exists for TODAY.
    Returns: (total_xp, total_boss_kills, ehp, ehb, raw_data) or None
    """
    conn = get_connection()
    c = conn.cursor()
    
    # Define "Today" as the current local date prefix YYYY-MM-DD
    # Timestamps in DB are ISO strings: YYYY-MM-DDTHH:MM:SS.mmmmmm
    today_prefix = datetime.now().isoformat()[:10]  # First 10 chars is YYYY-MM-DD
    
    try:
        # We search for any timestamp starting with today's date
        c.execute('''
            SELECT total_xp, total_boss_kills, ehp, ehb, raw_data 
            FROM wom_snapshots 
            WHERE username = ? AND timestamp LIKE ?
            ORDER BY timestamp DESC
            LIMIT 1
        ''', (username.lower(), f"{today_prefix}%"))
        
        return c.fetchone()
    except Exception as e:
        print(f"Error checking today's snapshot for {username}: {e}")
        return None
    finally:
        conn.close()

def get_last_active_users():
    """
    Returns a list of usernames from the most recent fetch in wom_records.
    Used to detect users who have 'disappeared' since the last run.
    """
    conn = get_connection()
    c = conn.cursor()
    try:
        # Get latest date
        c.execute('SELECT MAX(fetch_date) FROM wom_records')
        last_date = c.fetchone()[0]
        
        if not last_date:
            return []
            
        c.execute('SELECT username FROM wom_records WHERE fetch_date = ?', (last_date,))
        return [row[0] for row in c.fetchall()]
    except Exception as e:
        print(f"Error getting last active users: {e}")
        return []
    finally:
        conn.close()

def update_username(old_username, new_username):
    """
    Updates a username across all tables.
    Used when a name change is detected.
    Returns: True if successful, False otherwise.
    """
    conn = get_connection()
    c = conn.cursor()
    
    try:
        # 1. Update Discord Messages
        c.execute('UPDATE discord_messages SET author_name = ? WHERE author_name = ?', (new_username, old_username))
        discord_count = c.rowcount
        
        # 2. Update WOM Records
        c.execute('UPDATE wom_records SET username = ? WHERE username = ?', (new_username, old_username))
        records_count = c.rowcount
        
        # 3. Update WOM Snapshots
        c.execute('UPDATE wom_snapshots SET username = ? WHERE username = ?', (new_username, old_username))
        snapshots_count = c.rowcount
        
        conn.commit()
        print(f"Name change applied: '{old_username}' -> '{new_username}' (Discord: {discord_count}, Records: {records_count}, Snapshots: {snapshots_count})")
        return True
    except Exception as e:
        print(f"Error updating username {old_username} -> {new_username}: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()
