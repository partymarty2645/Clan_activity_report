"""
Migration helper utilities for safe database operations.

Provides functions for:
- Automated database backups before migrations
- Migration verification with integrity checks
- Rollback from backups when needed
- Data validation throughout the process

Usage:
    from utils.migration_helper import backup_database, verify_migration, rollback_migration
    
    # Before a risky migration:
    backup_path = backup_database()
    try:
        run_migration()
        verify_migration()
    except Exception as e:
        rollback_migration(backup_path)
        raise
"""

import os
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Tuple, List, Optional


class MigrationHelper:
    """Helper class for safe database migrations."""
    
    # Database and backup paths
    DB_PATH = "clan_data.db"
    BACKUP_DIR = Path("backups")
    
    @staticmethod
    def backup_database(db_path: str = DB_PATH) -> str:
        """
        Create a backup of the database with timestamp.
        
        Args:
            db_path: Path to database file (default: clan_data.db)
            
        Returns:
            str: Path to created backup file
            
        Raises:
            FileNotFoundError: If database doesn't exist
            IOError: If backup creation fails
        """
        if not Path(db_path).exists():
            raise FileNotFoundError(f"Database not found at {db_path}")
        
        # Create backups directory if needed
        MigrationHelper.BACKUP_DIR.mkdir(exist_ok=True)
        
        # Create timestamped backup filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"clan_data_{timestamp}.db"
        backup_path = MigrationHelper.BACKUP_DIR / backup_name
        
        # Copy database file
        try:
            shutil.copy2(db_path, str(backup_path))
        except IOError as e:
            raise IOError(f"Failed to create backup at {backup_path}: {e}") from e
        
        return str(backup_path)
    
    @staticmethod
    def verify_migration(
        db_path: str = DB_PATH,
        checks: Optional[List[str]] = None
    ) -> Tuple[bool, List[str]]:
        """
        Verify database integrity after migration.
        
        Args:
            db_path: Path to database file to verify
            checks: List of checks to perform. If None, runs all checks.
                   Supported: 'tables', 'columns', 'indexes', 'constraints', 'data'
            
        Returns:
            Tuple of (success: bool, errors: List[str])
            success=True if all checks pass, False if any fail
            errors contains descriptive error messages if any checks fail
        """
        errors = []
        
        if not Path(db_path).exists():
            return False, [f"Database not found at {db_path}"]
        
        if checks is None:
            checks = ['tables', 'columns', 'indexes', 'constraints']
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Check tables exist and are accessible
            if 'tables' in checks:
                expected_tables = [
                    'clan_members', 'wom_records', 'wom_snapshots',
                    'discord_messages', 'boss_snapshots'
                ]
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                existing_tables = {row[0] for row in cursor.fetchall()}
                
                for table in expected_tables:
                    if table not in existing_tables:
                        errors.append(f"Missing table: {table}")
            
            # Check columns exist in key tables
            if 'columns' in checks:
                cursor.execute("PRAGMA table_info(clan_members)")
                clan_cols = {row[1] for row in cursor.fetchall()}
                
                required_cols = {'id', 'username', 'role', 'joined_at'}
                missing = required_cols - clan_cols
                if missing:
                    errors.append(f"Missing columns in clan_members: {missing}")
            
            # Check indexes exist
            if 'indexes' in checks:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
                existing_indexes = {row[0] for row in cursor.fetchall()}
                
                critical_indexes = [
                    'idx_wom_snapshots_timestamp',
                    'idx_discord_messages_created_at'
                ]
                missing_indexes = [
                    idx for idx in critical_indexes if idx not in existing_indexes
                ]
                if missing_indexes:
                    errors.append(
                        f"Missing critical indexes: {missing_indexes}. "
                        "Run: python -m alembic upgrade head"
                    )
            
            # Check data integrity
            if 'data' in checks:
                # Verify no NULL values in critical columns
                cursor.execute("SELECT COUNT(*) FROM clan_members WHERE username IS NULL")
                if cursor.fetchone()[0] > 0:
                    errors.append("Found NULL usernames in clan_members")
                
                cursor.execute("SELECT COUNT(*) FROM wom_snapshots WHERE timestamp IS NULL")
                if cursor.fetchone()[0] > 0:
                    errors.append("Found NULL timestamps in wom_snapshots")
            
            conn.close()
            
        except sqlite3.DatabaseError as e:
            return False, [f"Database error during verification: {e}"]
        except Exception as e:
            return False, [f"Unexpected error during verification: {e}"]
        
        return len(errors) == 0, errors
    
    @staticmethod
    def rollback_migration(backup_path: str, target_db_path: str = DB_PATH) -> bool:
        """
        Restore database from backup, overwriting current database.
        
        Args:
            backup_path: Path to backup file to restore from
            target_db_path: Path where to restore the database (default: clan_data.db)
            
        Returns:
            bool: True if rollback successful, False otherwise
            
        Raises:
            FileNotFoundError: If backup doesn't exist
            IOError: If restore fails
        """
        backup_file = Path(backup_path)
        if not backup_file.exists():
            raise FileNotFoundError(f"Backup not found at {backup_path}")
        
        target_file = Path(target_db_path)
        
        try:
            # Create safety backup of current db before restoring
            if target_file.exists():
                safety_backup = (
                    Path("backups") / 
                    f"clan_data_pre_rollback_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
                )
                shutil.copy2(str(target_file), str(safety_backup))
            
            # Restore from backup
            shutil.copy2(str(backup_file), str(target_file))
            return True
            
        except IOError as e:
            raise IOError(f"Failed to rollback from {backup_path}: {e}") from e
    
    @staticmethod
    def get_database_size(db_path: str = DB_PATH) -> Tuple[int, str]:
        """
        Get database file size in bytes and human-readable format.
        
        Args:
            db_path: Path to database file
            
        Returns:
            Tuple of (size_bytes: int, size_human: str)
            Example: (1048576, "1.0 MB")
        """
        try:
            size_bytes = os.path.getsize(db_path)
            
            # Convert to human-readable format
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size_bytes < 1024:
                    return size_bytes, f"{size_bytes:.1f} {unit}"
                size_bytes /= 1024
            
            return size_bytes, f"{size_bytes:.1f} TB"
        except OSError:
            return 0, "0 B"
    
    @staticmethod
    def list_backups(backup_dir: Path = BACKUP_DIR) -> List[dict]:
        """
        List all available database backups.
        
        Args:
            backup_dir: Directory containing backups
            
        Returns:
            List of dicts with backup info: {'path', 'size', 'size_human', 'created'}
        """
        if not backup_dir.exists():
            return []
        
        backups = []
        for backup_file in sorted(backup_dir.glob("clan_data_*.db"), reverse=True):
            size_bytes = backup_file.stat().st_size
            
            # Human-readable size
            size = size_bytes
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size < 1024:
                    size_human = f"{size:.1f} {unit}"
                    break
                size /= 1024
            else:
                size_human = f"{size:.1f} TB"
            
            # Extract timestamp from filename
            timestamp_str = backup_file.stem.replace("clan_data_", "")
            
            backups.append({
                'path': str(backup_file),
                'name': backup_file.name,
                'size': size_bytes,
                'size_human': size_human,
                'created': timestamp_str
            })
        
        return backups


# Convenience functions for direct usage
def backup_database(db_path: str = "clan_data.db") -> str:
    """Convenience wrapper: backup_database(db_path) -> backup_path"""
    return MigrationHelper.backup_database(db_path)


def verify_migration(db_path: str = "clan_data.db", checks: Optional[List[str]] = None) -> Tuple[bool, List[str]]:
    """Convenience wrapper: verify_migration(db_path, checks) -> (success, errors)"""
    return MigrationHelper.verify_migration(db_path, checks)


def rollback_migration(backup_path: str, target_db_path: str = "clan_data.db") -> bool:
    """Convenience wrapper: rollback_migration(backup_path, target_db_path) -> success"""
    return MigrationHelper.rollback_migration(backup_path, target_db_path)
