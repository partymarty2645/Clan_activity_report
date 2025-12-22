
import sqlite3
import datetime
import os
import sys
import logging
from datetime import timezone, timedelta

# Ensure root path is in sys.path
sys.path.append(os.getcwd())

# Import Reporter but NOT database/services that rely on ORM
# reporting.excel imports pandas and xlsxwriter. It lazily imports database if needed.
# We will provide the service, so it won't trigger lazy import.
from reporting.excel import reporter
from core.config import Config
from core.usernames import UsernameNormalizer
from data.queries import Queries

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("ReportSQLite")

DB_PATH = "clan_data.db"

class SQLiteAnalyticsService:
    def __init__(self, db_path):
        self.db_path = db_path

    def _get_conn(self):
        return sqlite3.connect(self.db_path)

    def get_latest_snapshots(self):
        """Returns {username: {id, timestamp, xp, total_boss, total_xp, msgs...}}"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # Get Max Timestamp per user
        cursor.execute(Queries.GET_LATEST_SNAPSHOTS)
        rows = cursor.fetchall()
        conn.close()
        
        # Map to format expected by reporter
        result = {}
        for r in rows:
            result[r[1]] = {
                'id': r[0],
                'username': r[1],
                'timestamp': r[2], 
                'total_xp': r[3],
                'total_boss_kills': r[4], 
                # For compatibility, map nice keys
                'xp': r[3],
                'boss': r[4]
            }
        return result

    def get_snapshots_at_cutoff(self, cutoff_dt):
        """
        Returns one snapshot per user <= cutoff_dt.
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cutoff_str = cutoff_dt.isoformat()
        
        cursor.execute(Queries.GET_SNAPSHOTS_AT_CUTOFF, (cutoff_str,))
        
        rows = cursor.fetchall()
        conn.close()
        
        result = {}
        for r in rows:
            result[r[1]] = {
                'id': r[0],
                'username': r[1],
                'timestamp': r[2],
                'total_xp': r[3],
                'total_boss_kills': r[4],
                'xp': r[3],
                'boss': r[4]
            }
        return result

    def get_message_counts(self, cutoff_dt):
        """
        Returns {username: count} for messages >= cutoff_dt
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cutoff_str = cutoff_dt.isoformat()
        
        # 1. Get List of Known Clan Members for Robust Matching
        cursor.execute(Queries.GET_ALL_MEMBERS_METADATA)
        members = [r[0] for r in cursor.fetchall()]
        
        # Build normalized map for matching Discord authors to clan members
        nm_map = {UsernameNormalizer.normalize(m): m for m in members}
        
        cutoff_str = cutoff_dt.isoformat()
        
        # 2. Get All Discord Message Counts (Grouped by raw author name)
        cursor.execute(Queries.GET_DISCORD_MSG_COUNTS_SINCE, (cutoff_str,))
        
        rows = cursor.fetchall()
        conn.close()
        
        result = {}
        
        for author, count in rows:
            # Try to match to a clan member
            if not author: continue
            
            target_user = None
            normalized = UsernameNormalizer.normalize(author)
            
            if normalized in nm_map:
                target_user = nm_map[normalized]
            else:
                target_user = author.lower() 
                
            result[target_user] = result.get(target_user, 0) + count
            
        return result
    
    def get_min_timestamps(self):
        """Returns {username: {ts, xp, boss}} for first seen snapshot."""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute(Queries.GET_MIN_TIMESTAMPS)
        rows = cursor.fetchall()
        conn.close()
        return {r[0]: {'ts': r[1], 'xp': r[2], 'boss': r[3]} for r in rows}

    def calculate_gains(self, latest_snaps, past_snaps, staleness_limit_days=None):
        """
        Returns {username: {'xp': val, 'boss': val}}
        """
        gains = {}
        # Pre-fetch min timestamps for fallback
        min_snaps = self.get_min_timestamps()
        
        for user, current in latest_snaps.items():
            past = past_snaps.get(user)
            
            # Fallback logic: If no past snapshot (e.g. <30d ago), use first seen
            fallback_used = False
            if not past and user in min_snaps:
                first_seen = min_snaps[user]
                # Only use if first_seen is older than current
                if first_seen['ts'] < current['timestamp']:
                    past = {
                        'xp': first_seen['xp'],
                        'boss': first_seen['boss'],
                        'ts': first_seen['ts'] # Ensure ts is present
                    }
                    fallback_used = True
            
            if past and staleness_limit_days:
                try:
                    curr_ts = datetime.datetime.fromisoformat(current['timestamp'].replace('Z', '+00:00'))
                    past_ts_str = past.get('timestamp') or past.get('ts')
                    if past_ts_str:
                         past_ts = datetime.datetime.fromisoformat(past_ts_str.replace('Z', '+00:00'))
                         days_diff = (curr_ts - past_ts).days
                         if days_diff > staleness_limit_days:
                             # Too old for this specific stat window, reset to 0
                             past = None 
                except Exception:
                     pass

            if past:
                xp_gain = current['total_xp'] - past['xp']
                boss_gain = current['total_boss_kills'] - past['boss']
                gains[user] = {
                    'xp': max(0, xp_gain),
                    'boss': max(0, boss_gain)
                }
            else:
                # New user or no recent history
                gains[user] = {'xp': 0, 'boss': 0}
        return gains

def load_metadata(db_path, min_timestamps=None):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(Queries.GET_ALL_MEMBERS_METADATA)
    rows = cursor.fetchall()
    conn.close()
    
    # Metadata for reporter: objects with .role / .joined_at attributes OR dicts .get()
    
    CLAN_FOUNDING_DATE = datetime.datetime(2025, 2, 14, tzinfo=timezone.utc)
    
    metadata = {}
    for r in rows:
        username = r[0]
        role = r[1]
        joined_at_str = r[2]
        
        joined_dt = None
        
        # 1. Try DB joined_at
        if joined_at_str:
            try:
                joined_dt = datetime.datetime.fromisoformat(joined_at_str.replace('Z', '+00:00'))
            except:
                pass
        
        # 2. Fallback to Min Snapshot
        if not joined_dt and min_timestamps and username in min_timestamps:
            try:
                min_ts_str = min_timestamps[username]['ts']
                joined_dt = datetime.datetime.fromisoformat(min_ts_str.replace('Z', '+00:00'))
            except:
                pass
        
        # 3. Clamp to Clan Founding Date
        if joined_dt:
            if joined_dt.tzinfo is None:
                joined_dt = joined_dt.replace(tzinfo=timezone.utc)
            if joined_dt < CLAN_FOUNDING_DATE:
                joined_dt = CLAN_FOUNDING_DATE
        
        metadata[username.lower()] = {
            'username': username,
            'role': role,
            'joined_at': joined_dt.strftime('%Y-%m-%d') if joined_dt else None
        }
    return metadata

def run_report_sync():
    logger.info("Starting SQLite-based Report Generation...")
    
    analytics = SQLiteAnalyticsService(DB_PATH)
    
    # Fetch min timestamps for metadata fallback
    min_ts = analytics.get_min_timestamps()
    metadata = load_metadata(DB_PATH, min_ts)
    
    logger.info(f"Loaded metadata for {len(metadata)} users.")
    
    try:
        reporter.generate(analytics, metadata=metadata)
        logger.info("Report generation completed via SQLite adapter.")
        
        # Export to Drive if configured
        drive_path = Config.LOCAL_DRIVE_PATH
        if drive_path and os.path.exists(drive_path):
            import shutil
            
            # Export Data Report
            data_file = "clan_report_data.xlsx"
            if os.path.exists(data_file):
                try:
                    shutil.copy(data_file, os.path.join(drive_path, data_file))
                    logger.info(f"Successfully exported {data_file} to {drive_path}")
                except Exception as e:
                    logger.error(f"Failed to export {data_file} to Drive: {e}")
            
            # Export Full (Dashboard) Report
            full_file = "clan_report_full.xlsx"
            if os.path.exists(full_file):
                try:
                    shutil.copy(full_file, os.path.join(drive_path, full_file))
                    logger.info(f"Successfully exported {full_file} to {drive_path}")
                except Exception as e:
                    logger.error(f"Failed to export {full_file} to Drive: {e}")
            
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_report_sync()
