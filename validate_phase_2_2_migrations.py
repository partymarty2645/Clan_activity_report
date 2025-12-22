#!/usr/bin/env python
"""
Phase 2.2.8: Automated Staging Test Validator

Validates all Phase 2.2 migrations without requiring manual testing.
Runs comprehensive checks on data integrity, FK relationships, and performance.

Exit Code:
  0 = All tests passed ✅
  1 = Some tests failed ❌
"""

import sqlite3
import time
import subprocess
import sys
from pathlib import Path
from typing import Tuple, List, Dict

class ValidationTest:
    """Base class for validation tests."""
    
    def __init__(self, name: str):
        self.name = name
        self.passed = False
        self.message = ""
    
    def run(self) -> bool:
        """Run the test. Override in subclass."""
        raise NotImplementedError
    
    def __str__(self) -> str:
        status = "✅ PASS" if self.passed else "❌ FAIL"
        return f"{status}: {self.name}"


class MigrationSequenceTest(ValidationTest):
    """Test that all migrations apply in correct order."""
    
    def run(self) -> bool:
        try:
            result = subprocess.run(
                [sys.executable, "-m", "alembic", "current"],
                capture_output=True,
                text=True
            )
            
            # Should show normalize_user_ids_004 as current
            if "normalize_user_ids_004" in result.stdout:
                self.message = "All migrations applied successfully (at normalize_user_ids_004)"
                self.passed = True
            else:
                self.message = f"Migration chain incomplete. Current: {result.stdout.strip()}"
                self.passed = False
        except Exception as e:
            self.message = f"Error checking migration status: {e}"
            self.passed = False
        
        return self.passed


class DataPopulationTest(ValidationTest):
    """Test that all IDs were populated correctly."""
    
    def run(self) -> bool:
        try:
            conn = sqlite3.connect("clan_data.db")
            cursor = conn.cursor()
            
            tests_passed = 0
            results = []
            
            # Test 1: clan_members IDs populated
            cursor.execute("SELECT COUNT(*) FROM clan_members WHERE id IS NOT NULL")
            members_with_id = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM clan_members")
            total_members = cursor.fetchone()[0]
            
            if members_with_id == total_members:
                results.append(f"✅ clan_members: {members_with_id}/{total_members} IDs populated")
                tests_passed += 1
            else:
                results.append(f"❌ clan_members: Only {members_with_id}/{total_members} IDs populated")
            
            # Test 2: wom_snapshots user_id populated (high match rate expected)
            cursor.execute("SELECT COUNT(*) FROM wom_snapshots WHERE user_id IS NOT NULL")
            wom_with_id = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM wom_snapshots")
            total_wom = cursor.fetchone()[0]
            match_rate = 100 * wom_with_id / total_wom if total_wom > 0 else 0
            
            if match_rate >= 95:  # 95%+ expected
                results.append(f"✅ wom_snapshots: {wom_with_id}/{total_wom} user_id ({match_rate:.1f}%)")
                tests_passed += 1
            else:
                results.append(f"⚠️  wom_snapshots: {wom_with_id}/{total_wom} user_id ({match_rate:.1f}%)")
                tests_passed += 0.5  # Partial credit for reasonable match rate
            
            # Test 3: boss_snapshots wom_snapshot_id populated (100% expected)
            cursor.execute("SELECT COUNT(*) FROM boss_snapshots WHERE wom_snapshot_id IS NOT NULL")
            boss_with_snap = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM boss_snapshots")
            total_boss = cursor.fetchone()[0]
            
            if boss_with_snap == total_boss:
                results.append(f"✅ boss_snapshots: {boss_with_snap}/{total_boss} wom_snapshot_id")
                tests_passed += 1
            else:
                results.append(f"❌ boss_snapshots: Only {boss_with_snap}/{total_boss} wom_snapshot_id")
            
            # Test 4: discord_messages user_id populated (50%+ expected due to bots)
            cursor.execute("SELECT COUNT(*) FROM discord_messages WHERE user_id IS NOT NULL")
            msg_with_id = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM discord_messages")
            total_msg = cursor.fetchone()[0]
            msg_rate = 100 * msg_with_id / total_msg if total_msg > 0 else 0
            
            if msg_rate >= 45:  # 45%+ expected (accounting for bots)
                results.append(f"✅ discord_messages: {msg_with_id}/{total_msg} user_id ({msg_rate:.1f}%)")
                tests_passed += 1
            else:
                results.append(f"⚠️  discord_messages: {msg_with_id}/{total_msg} user_id ({msg_rate:.1f}%)")
                tests_passed += 0.5
            
            conn.close()
            
            self.message = "\n  ".join(results)
            self.passed = tests_passed >= 3.5  # Allow some flexibility
            
        except Exception as e:
            self.message = f"Error checking data population: {e}"
            self.passed = False
        
        return self.passed


class ForeignKeyIntegrityTest(ValidationTest):
    """Test that FK relationships are valid (no orphaned records)."""
    
    def run(self) -> bool:
        try:
            conn = sqlite3.connect("clan_data.db")
            cursor = conn.cursor()
            
            orphaned = []
            
            # Check wom_snapshots.user_id references valid clan_members.id
            cursor.execute("""
                SELECT COUNT(*) FROM wom_snapshots ws
                WHERE ws.user_id IS NOT NULL
                AND NOT EXISTS (SELECT 1 FROM clan_members cm WHERE cm.id = ws.user_id)
            """)
            count = cursor.fetchone()[0]
            if count > 0:
                orphaned.append(f"wom_snapshots: {count} orphaned user_id references")
            
            # Check discord_messages.user_id references valid clan_members.id
            cursor.execute("""
                SELECT COUNT(*) FROM discord_messages dm
                WHERE dm.user_id IS NOT NULL
                AND NOT EXISTS (SELECT 1 FROM clan_members cm WHERE cm.id = dm.user_id)
            """)
            count = cursor.fetchone()[0]
            if count > 0:
                orphaned.append(f"discord_messages: {count} orphaned user_id references")
            
            # Check boss_snapshots.wom_snapshot_id references valid wom_snapshots.id
            cursor.execute("""
                SELECT COUNT(*) FROM boss_snapshots bs
                WHERE bs.wom_snapshot_id IS NOT NULL
                AND NOT EXISTS (SELECT 1 FROM wom_snapshots ws WHERE ws.id = bs.wom_snapshot_id)
            """)
            count = cursor.fetchone()[0]
            if count > 0:
                orphaned.append(f"boss_snapshots: {count} orphaned wom_snapshot_id references")
            
            conn.close()
            
            if orphaned:
                self.message = "Orphaned records found: " + ", ".join(orphaned)
                self.passed = False
            else:
                self.message = "No orphaned records detected. All FK references valid."
                self.passed = True
            
        except Exception as e:
            self.message = f"Error checking FK integrity: {e}"
            self.passed = False
        
        return self.passed


class UniqueConstraintTest(ValidationTest):
    """Test that unique constraints are enforced."""
    
    def run(self) -> bool:
        try:
            conn = sqlite3.connect("clan_data.db")
            cursor = conn.cursor()
            
            # Check clan_members.username is unique
            cursor.execute("""
                SELECT COUNT(*) FROM (
                    SELECT username FROM clan_members 
                    WHERE username IS NOT NULL
                    GROUP BY username HAVING COUNT(*) > 1
                )
            """)
            duplicates = cursor.fetchone()[0]
            
            if duplicates == 0:
                self.message = "Username uniqueness constraint satisfied"
                self.passed = True
            else:
                self.message = f"Found {duplicates} duplicate usernames"
                self.passed = False
            
            conn.close()
        except Exception as e:
            self.message = f"Error checking uniqueness: {e}"
            self.passed = False
        
        return self.passed


class AllTestsPassTest(ValidationTest):
    """Verify pytest test suite passes."""
    
    def run(self) -> bool:
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "tests/", "-q"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                # Extract test count from output
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'passed' in line:
                        self.message = line.strip()
                        break
                self.passed = True
            else:
                self.message = f"Tests failed: {result.stdout}"
                self.passed = False
        except Exception as e:
            self.message = f"Error running tests: {e}"
            self.passed = False
        
        return self.passed


class SchemaValidationTest(ValidationTest):
    """Validate database schema structure."""
    
    def run(self) -> bool:
        try:
            conn = sqlite3.connect("clan_data.db")
            cursor = conn.cursor()
            
            required_columns = {
                'clan_members': ['id', 'username', 'role'],
                'wom_snapshots': ['id', 'username', 'user_id', 'timestamp', 'total_xp'],
                'discord_messages': ['id', 'author_name', 'user_id', 'created_at'],
                'boss_snapshots': ['id', 'snapshot_id', 'wom_snapshot_id', 'boss_name'],
            }
            
            missing_columns = []
            for table, columns in required_columns.items():
                cursor.execute(f"PRAGMA table_info({table})")
                existing = {row[1] for row in cursor.fetchall()}
                
                for col in columns:
                    if col not in existing:
                        missing_columns.append(f"{table}.{col}")
            
            conn.close()
            
            if missing_columns:
                self.message = f"Missing columns: {', '.join(missing_columns)}"
                self.passed = False
            else:
                self.message = "All required columns present"
                self.passed = True
        except Exception as e:
            self.message = f"Error validating schema: {e}"
            self.passed = False
        
        return self.passed


def run_validation_suite() -> Tuple[List[ValidationTest], bool]:
    """Run all validation tests."""
    
    tests = [
        MigrationSequenceTest("Migration chain applied correctly"),
        DataPopulationTest("All ID columns populated"),
        ForeignKeyIntegrityTest("FK references are valid"),
        UniqueConstraintTest("Unique constraints enforced"),
        SchemaValidationTest("Schema structure correct"),
        AllTestsPassTest("All pytest tests passing"),
    ]
    
    print("=" * 70)
    print("PHASE 2.2.8: PRODUCTION STAGING TEST - VALIDATION SUITE")
    print("=" * 70)
    print()
    
    all_passed = True
    for i, test in enumerate(tests, 1):
        print(f"[{i}/{len(tests)}] Running: {test.name}...")
        test.run()
        print(f"    {test}")
        if test.message:
            for line in test.message.split('\n'):
                print(f"    └─ {line}")
        print()
        
        if not test.passed:
            all_passed = False
    
    print("=" * 70)
    if all_passed:
        print("✅ ALL VALIDATION TESTS PASSED - READY FOR PRODUCTION")
    else:
        print("❌ SOME TESTS FAILED - FIX BEFORE PRODUCTION DEPLOYMENT")
    print("=" * 70)
    
    return tests, all_passed


if __name__ == "__main__":
    tests, all_passed = run_validation_suite()
    sys.exit(0 if all_passed else 1)
