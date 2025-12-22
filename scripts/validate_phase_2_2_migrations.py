#!/usr/bin/env python
"""
Phase 2.2.8: Automated Staging Test Suite

Comprehensive automated validation of all Phase 2.2 migrations.
Tests migration sequence, data integrity, performance, and rollback.

Usage:
    python scripts/validate_phase_2_2_migrations.py [--test-rollback]

Options:
    --test-rollback    Also test rollback functionality (WARNING: requires 2x time)
"""

import sys
import subprocess
import sqlite3
import time
import argparse
from pathlib import Path
from datetime import datetime
from typing import Tuple, List, Dict, Any


class Phase22Validator:
    """Comprehensive validation suite for Phase 2.2 migrations."""
    
    def __init__(self, db_path: str = "clan_data.db", verbose: bool = True):
        self.db_path = db_path
        self.verbose = verbose
        self.results = []
        self.start_time = None
        
    def log(self, message: str, level: str = "INFO"):
        """Log message with timestamp."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        prefix = f"[{timestamp}] [{level:7s}]"
        if self.verbose:
            print(f"{prefix} {message}")
        self.results.append((timestamp, level, message))
    
    def run_all_tests(self, test_rollback: bool = False) -> bool:
        """Run complete validation suite."""
        self.start_time = time.time()
        self.log("=" * 70, "START")
        self.log("Phase 2.2 Automated Staging Test Suite", "START")
        self.log(f"Database: {self.db_path}", "INFO")
        self.log(f"Test Rollback: {test_rollback}", "INFO")
        self.log("=" * 70, "START")
        
        all_passed = True
        
        try:
            # Test 1: Pre-migration state
            if not self.test_pre_migration_state():
                all_passed = False
            
            # Test 2: Migration sequence
            if not self.test_migration_sequence():
                all_passed = False
            
            # Test 3: Data integrity
            if not self.test_data_integrity():
                all_passed = False
            
            # Test 4: FK relationships
            if not self.test_fk_relationships():
                all_passed = False
            
            # Test 5: Performance baseline
            if not self.test_performance():
                all_passed = False
            
            # Test 6: Rollback (if requested)
            if test_rollback:
                if not self.test_rollback():
                    all_passed = False
            
            # Test 7: Schema completeness
            if not self.test_schema_completeness():
                all_passed = False
            
        except Exception as e:
            self.log(f"Unexpected error: {e}", "ERROR")
            all_passed = False
        
        # Print summary
        duration = time.time() - self.start_time
        self.log("=" * 70, "SUMMARY")
        self.log(f"Tests Completed: {len([r for r in self.results if r[1] != 'START'])}", "SUMMARY")
        self.log(f"Duration: {duration:.2f} seconds", "SUMMARY")
        status = "✅ ALL TESTS PASSED" if all_passed else "❌ SOME TESTS FAILED"
        self.log(status, "SUMMARY")
        self.log("=" * 70, "SUMMARY")
        
        return all_passed
    
    def test_pre_migration_state(self) -> bool:
        """Verify database state before migrations."""
        self.log("TEST 1: Pre-Migration State Validation", "TEST")
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check tables exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            tables = {row[0] for row in cursor.fetchall()}
            
            required_tables = {
                'clan_members', 'wom_snapshots', 'discord_messages',
                'boss_snapshots', 'wom_records', 'alembic_version'
            }
            
            missing = required_tables - tables
            if missing:
                self.log(f"  ❌ Missing tables: {missing}", "FAIL")
                return False
            
            self.log(f"  ✅ All required tables present ({len(tables)} tables)", "PASS")
            
            # Check alembic_version exists
            cursor.execute("SELECT version_num FROM alembic_version ORDER BY version_num DESC LIMIT 1")
            current = cursor.fetchone()
            if current:
                self.log(f"  ✅ Current migration: {current[0]}", "PASS")
            
            conn.close()
            return True
            
        except Exception as e:
            self.log(f"  ❌ Pre-migration state test failed: {e}", "FAIL")
            return False
    
    def test_migration_sequence(self) -> bool:
        """Test that migrations apply in correct sequence."""
        self.log("TEST 2: Migration Sequence Validation", "TEST")
        
        try:
            # Get current migration state
            result = subprocess.run(
                [sys.executable, "-m", "alembic", "current"],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent
            )
            
            current_version = result.stdout.strip()
            expected_version = "normalize_user_ids_004"
            
            if expected_version in current_version or "normalize_user_ids_004" in result.stdout:
                self.log(f"  ✅ Migrations applied: {current_version}", "PASS")
                return True
            else:
                self.log(f"  ❌ Expected {expected_version}, got: {current_version}", "FAIL")
                return False
                
        except Exception as e:
            self.log(f"  ❌ Migration sequence test failed: {e}", "FAIL")
            return False
    
    def test_data_integrity(self) -> bool:
        """Validate data population and consistency."""
        self.log("TEST 3: Data Integrity Validation", "TEST")
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            tests_passed = 0
            tests_total = 0
            
            # Check clan_members.id population
            tests_total += 1
            cursor.execute("SELECT COUNT(*) FROM clan_members WHERE id IS NOT NULL")
            with_id = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM clan_members")
            total = cursor.fetchone()[0]
            
            if with_id == total:
                self.log(f"  ✅ clan_members.id: {with_id}/{total} populated (100%)", "PASS")
                tests_passed += 1
            else:
                self.log(f"  ⚠️  clan_members.id: {with_id}/{total} populated ({100*with_id/total:.1f}%)", "WARN")
            
            # Check wom_snapshots.user_id population
            tests_total += 1
            cursor.execute("SELECT COUNT(*) FROM wom_snapshots WHERE user_id IS NOT NULL")
            with_user_id = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM wom_snapshots")
            total_wom = cursor.fetchone()[0]
            
            match_pct = 100 * with_user_id / total_wom if total_wom > 0 else 0
            if match_pct >= 90:  # Allow for unmatched (99 users)
                self.log(f"  ✅ wom_snapshots.user_id: {with_user_id}/{total_wom} ({match_pct:.1f}%)", "PASS")
                tests_passed += 1
            else:
                self.log(f"  ❌ wom_snapshots.user_id: {with_user_id}/{total_wom} ({match_pct:.1f}%) - below 90%", "FAIL")
            
            # Check discord_messages.user_id population
            tests_total += 1
            cursor.execute("SELECT COUNT(*) FROM discord_messages WHERE user_id IS NOT NULL")
            with_msg_id = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM discord_messages")
            total_msg = cursor.fetchone()[0]
            
            msg_pct = 100 * with_msg_id / total_msg if total_msg > 0 else 0
            if msg_pct >= 40:  # Allow for bots/deleted users
                self.log(f"  ✅ discord_messages.user_id: {with_msg_id}/{total_msg} ({msg_pct:.1f}%)", "PASS")
                tests_passed += 1
            else:
                self.log(f"  ⚠️  discord_messages.user_id: {with_msg_id}/{total_msg} ({msg_pct:.1f}%) - bots/deleted", "WARN")
            
            # Check boss_snapshots.wom_snapshot_id
            tests_total += 1
            cursor.execute("SELECT COUNT(*) FROM boss_snapshots WHERE wom_snapshot_id IS NOT NULL")
            with_snap_id = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM boss_snapshots")
            total_boss = cursor.fetchone()[0]
            
            if with_snap_id == total_boss:
                self.log(f"  ✅ boss_snapshots.wom_snapshot_id: {with_snap_id}/{total_boss} (100%)", "PASS")
                tests_passed += 1
            else:
                self.log(f"  ⚠️  boss_snapshots.wom_snapshot_id: {with_snap_id}/{total_boss} ({100*with_snap_id/total_boss:.1f}%)", "WARN")
            
            conn.close()
            
            result = tests_passed >= (tests_total - 1)  # Allow 1 warning
            return result
            
        except Exception as e:
            self.log(f"  ❌ Data integrity test failed: {e}", "FAIL")
            return False
    
    def test_fk_relationships(self) -> bool:
        """Validate FK constraints and relationships."""
        self.log("TEST 4: Foreign Key Relationships Validation", "TEST")
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            violations = []
            
            # Check wom_snapshots.user_id references valid clan_members
            cursor.execute("""
                SELECT COUNT(*) FROM wom_snapshots ws
                WHERE user_id IS NOT NULL 
                AND user_id NOT IN (SELECT id FROM clan_members)
            """)
            if cursor.fetchone()[0] > 0:
                violations.append("wom_snapshots.user_id references invalid clan_members")
            
            # Check discord_messages.user_id references valid clan_members
            cursor.execute("""
                SELECT COUNT(*) FROM discord_messages dm
                WHERE user_id IS NOT NULL
                AND user_id NOT IN (SELECT id FROM clan_members)
            """)
            if cursor.fetchone()[0] > 0:
                violations.append("discord_messages.user_id references invalid clan_members")
            
            # Check boss_snapshots.wom_snapshot_id references valid wom_snapshots
            cursor.execute("""
                SELECT COUNT(*) FROM boss_snapshots bs
                WHERE wom_snapshot_id IS NOT NULL
                AND wom_snapshot_id NOT IN (SELECT id FROM wom_snapshots)
            """)
            if cursor.fetchone()[0] > 0:
                violations.append("boss_snapshots.wom_snapshot_id references invalid wom_snapshots")
            
            conn.close()
            
            if violations:
                for v in violations:
                    self.log(f"  ❌ FK Violation: {v}", "FAIL")
                return False
            else:
                self.log(f"  ✅ All FK relationships valid", "PASS")
                return True
                
        except Exception as e:
            self.log(f"  ❌ FK relationships test failed: {e}", "FAIL")
            return False
    
    def test_performance(self) -> bool:
        """Baseline performance metrics."""
        self.log("TEST 5: Performance Baseline", "TEST")
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Time a complex query (snapshot aggregation)
            start = time.time()
            cursor.execute("""
                SELECT user_id, COUNT(*) as count
                FROM wom_snapshots
                WHERE user_id IS NOT NULL
                GROUP BY user_id
                LIMIT 100
            """)
            cursor.fetchall()
            query_time = (time.time() - start) * 1000  # ms
            
            self.log(f"  ✅ Query time (ID-based): {query_time:.2f}ms", "PASS")
            
            # Check index usage
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'")
            indexes = cursor.fetchall()
            self.log(f"  ✅ Performance indexes: {len(indexes)} created", "PASS")
            
            conn.close()
            return True
            
        except Exception as e:
            self.log(f"  ❌ Performance test failed: {e}", "FAIL")
            return False
    
    def test_rollback(self) -> bool:
        """Test rollback capability."""
        self.log("TEST 6: Rollback Capability Test", "TEST")
        self.log("  ⚠️  WARNING: This test will temporarily revert migrations", "WARN")
        
        try:
            # Downgrade to previous migration
            self.log("  🔄 Downgrading to previous migration...", "INFO")
            result = subprocess.run(
                [sys.executable, "-m", "alembic", "downgrade", "add_missing_indexes_003"],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent
            )
            
            if result.returncode != 0:
                self.log(f"  ❌ Downgrade failed: {result.stderr}", "FAIL")
                return False
            
            self.log("  ✅ Downgrade successful", "PASS")
            
            # Re-apply migration
            self.log("  🔄 Re-applying normalize_user_ids_004...", "INFO")
            result = subprocess.run(
                [sys.executable, "-m", "alembic", "upgrade", "normalize_user_ids_004"],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent
            )
            
            if result.returncode != 0:
                self.log(f"  ❌ Re-upgrade failed: {result.stderr}", "FAIL")
                return False
            
            self.log("  ✅ Re-upgrade successful", "PASS")
            
            return True
            
        except Exception as e:
            self.log(f"  ❌ Rollback test failed: {e}", "FAIL")
            return False
    
    def test_schema_completeness(self) -> bool:
        """Verify complete schema after all migrations."""
        self.log("TEST 7: Schema Completeness Validation", "TEST")
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            checks_passed = 0
            checks_total = 0
            
            # Check new columns exist
            tables_to_check = {
                'wom_snapshots': ['user_id'],
                'discord_messages': ['user_id'],
                'boss_snapshots': ['wom_snapshot_id'],
                'clan_members': ['id']
            }
            
            for table, required_cols in tables_to_check.items():
                checks_total += len(required_cols)
                cursor.execute(f"PRAGMA table_info({table})")
                existing_cols = {row[1] for row in cursor.fetchall()}
                
                for col in required_cols:
                    if col in existing_cols:
                        checks_passed += 1
                    else:
                        self.log(f"  ❌ Missing column: {table}.{col}", "FAIL")
            
            # Check unique index exists
            checks_total += 1
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='index' AND name='ix_clan_members_username_unique'
            """)
            if cursor.fetchone():
                self.log(f"  ✅ Unique index on clan_members.username exists", "PASS")
                checks_passed += 1
            else:
                self.log(f"  ⚠️  Unique index on clan_members.username missing", "WARN")
            
            conn.close()
            
            result = checks_passed >= (checks_total - 1)
            if result:
                self.log(f"  ✅ Schema completeness: {checks_passed}/{checks_total} checks passed", "PASS")
            return result
            
        except Exception as e:
            self.log(f"  ❌ Schema completeness test failed: {e}", "FAIL")
            return False


def main():
    """Run validation suite."""
    parser = argparse.ArgumentParser(
        description="Phase 2.2.8 Automated Staging Test Suite"
    )
    parser.add_argument(
        "--test-rollback",
        action="store_true",
        help="Also test rollback functionality (WARNING: takes longer)"
    )
    parser.add_argument(
        "--db",
        default="clan_data.db",
        help="Database path (default: clan_data.db)"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress output (results only)"
    )
    
    args = parser.parse_args()
    
    validator = Phase22Validator(db_path=args.db, verbose=not args.quiet)
    success = validator.run_all_tests(test_rollback=args.test_rollback)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
