class Queries:
    # --- HARVEST ---
    GET_LAST_MSG_DATE = "SELECT MAX(created_at) FROM discord_messages"
    
    UPSERT_MEMBER = '''
        INSERT OR REPLACE INTO clan_members (username, role, joined_at, last_updated)
        VALUES (?, ?, ?, ?)
    '''
    
    DELETE_STALE_MEMBERS = "DELETE FROM clan_members WHERE username NOT IN ({})"
    
    SELECT_MEMBER_COUNT = "SELECT COUNT(*) FROM clan_members"
    
    SELECT_MEMBERS_TO_DELETE = "SELECT COUNT(*) FROM clan_members WHERE username NOT IN ({})"

    INSERT_SNAPSHOT = '''
        INSERT INTO wom_snapshots (username, timestamp, total_xp, total_boss_kills, ehp, ehb, raw_data, user_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    '''
    
    INSERT_BOSS_SNAPSHOT = '''
        INSERT INTO boss_snapshots (snapshot_id, boss_name, kills, rank)
        VALUES (?, ?, ?, ?)
    '''

    CHECK_TODAY_SNAPSHOT = '''
        SELECT 1 
        FROM wom_snapshots ws
        WHERE ws.username = ? 
        AND date(ws.timestamp) = date('now')
        LIMIT 1
    '''

    # --- REPORT / EXPORT / SHARED ---
    
    GET_LATEST_SNAPSHOTS = '''
        SELECT id, username, timestamp, total_xp, total_boss_kills
        FROM (
            SELECT id, username, timestamp, total_xp, total_boss_kills,
                   ROW_NUMBER() OVER (PARTITION BY username ORDER BY timestamp DESC, id DESC) AS rn
            FROM wom_snapshots
        ) ranked
        WHERE rn = 1
    '''
    
    # Complex join to get the MIN timestamp row for each user
    GET_MIN_TIMESTAMPS = '''
        SELECT s.username, s.timestamp, s.total_xp, s.total_boss_kills
        FROM wom_snapshots s
        JOIN (
            SELECT username, MIN(timestamp) as min_ts
            FROM wom_snapshots
            GROUP BY username
        ) m ON s.username = m.username AND s.timestamp = m.min_ts
    '''
    
    GET_SNAPSHOTS_AT_CUTOFF = '''
        SELECT id, username, timestamp, total_xp, total_boss_kills
        FROM (
            SELECT id, username, timestamp, total_xp, total_boss_kills,
                   ROW_NUMBER() OVER (PARTITION BY username ORDER BY timestamp DESC, id DESC) AS rn
            FROM wom_snapshots
            WHERE timestamp <= ?
        ) ranked
        WHERE rn = 1
    '''

    GET_DISCORD_MSG_COUNTS_SINCE = '''
        SELECT author_name, COUNT(*)
        FROM discord_messages
        WHERE created_at >= ?
        GROUP BY author_name
    '''
    
    # --- EXPORT SPECIFIC ---
    
    GET_BOSS_DATA_CHUNK = '''
        SELECT snapshot_id, boss_name, kills 
        FROM boss_snapshots 
        WHERE snapshot_id IN ({})
    '''
    
    GET_DAILY_XP_MAX = '''
        SELECT date(timestamp) as day, username, MAX(total_xp) 
        FROM wom_snapshots 
        WHERE timestamp >= ?
        GROUP BY day, username
    '''
    
    GET_DAILY_MSGS = '''
        SELECT date(created_at) as day, COUNT(*) 
        FROM discord_messages 
        WHERE created_at >= ?
        GROUP BY day
    '''
    
    GET_BOSS_DIVERSITY = '''
        SELECT boss_name, SUM(kills)
        FROM boss_snapshots
        WHERE snapshot_id IN ({})
        GROUP BY boss_name
        ORDER BY SUM(kills) DESC
    '''
    
    GET_BOSS_SUMS_FOR_IDS = '''
        SELECT boss_name, SUM(kills)
        FROM boss_snapshots
        WHERE snapshot_id IN ({})
        GROUP BY boss_name
    '''

    GET_RAW_DATA_FOR_IDS = '''
        SELECT raw_data
        FROM wom_snapshots
        WHERE id IN ({})
    '''

    GET_DAILY_BOSS_KILLS = '''
        SELECT date(ws.timestamp) as day, SUM(bs.kills)
        FROM wom_snapshots ws
        JOIN boss_snapshots bs ON ws.id = bs.snapshot_id
        WHERE ws.timestamp >= ? AND bs.boss_name = ?
        GROUP BY day
    '''
    
    GET_DISCORD_MSG_COUNTS_TOTAL = "SELECT lower(author_name), COUNT(*) FROM discord_messages GROUP BY lower(author_name)"
    
    GET_DISCORD_MSG_COUNTS_SINCE_SIMPLE = '''
        SELECT lower(author_name), COUNT(*) 
        FROM discord_messages 
        WHERE created_at >= ? 
        GROUP BY lower(author_name)
    '''

    GET_HOURLY_ACTIVITY = '''
        SELECT strftime('%H', created_at) as hour, COUNT(*) 
        FROM discord_messages 
        WHERE created_at >= ? 
        GROUP BY hour
    '''

    GET_ALL_MEMBERS_METADATA = "SELECT username, role, joined_at FROM clan_members"
