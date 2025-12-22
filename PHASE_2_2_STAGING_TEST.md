
Phase 2.2.8: Production Staging Test Plan

This document outlines the manual testing required to validate all 5 migrations
before final production deployment.

CONTEXT:
- Phase 2.2 Database Schema Refactoring is 87.5% complete (7/8 tasks)
- 5 Alembic migrations have been created and tested successfully
- All code changes have been committed and tested
- This is the final validation step before going to production

MIGRATION SEQUENCE:
1. b1dda54d7b09_initial_schema.py - Initial setup
2. add_indexes_for_performance.py - Performance indexes (existing)
3. dedup_snaps_002.py - Unique snapshots constraint (existing)
4. drop_unused_tables.py (drop_unused_001) - Drop skill_snapshots ✅
5. add_missing_indexes.py (add_missing_indexes_003) - Performance indexes ✅
6. normalize_user_ids_004.py - Populate IDs and FK relationships ✅

STAGING TEST PROCEDURE:
================================================================

**Step 1: Database Backup & Copy to Staging**
```bash
# Create fresh backup
python scripts/backup_db.py

# Create test database copy on staging server
cp clan_data.db clan_data_staging.db
```

**Step 2: Test Migration Sequence**
```bash
# Run migrations in order
python -m alembic upgrade drop_unused_001    # Drop unused tables
python -m alembic upgrade add_missing_indexes_003  # Add indexes
python -m alembic upgrade normalize_user_ids_004   # Populate IDs
```

Expected results:
- No errors during migration execution
- All migrations recorded in alembic_version table
- Database remains accessible

**Step 3: Data Integrity Validation**
```bash
# Run integrity tests
pytest tests/test_database_integrity.py -v

# Check population results
- clan_members.id: Should be 305/305 populated
- wom_snapshots.user_id: Should be ~95,000+/96,000+ (98%+)
- discord_messages.user_id: Should be ~300,000+/586,000+ (50%+)
  (Lower % expected - includes bots, deleted users)
- boss_snapshots.wom_snapshot_id: Should be 427,557/427,557 (100%)
```

**Step 4: Performance Testing**
```bash
# Time report generation with old schema
time python scripts/report_sqlite.py > /dev/null
# Expected: 5-10 seconds

# Optimize with new ID-based queries
# (Code changes to use new methods)
time python scripts/report_sqlite.py > /dev/null
# Expected: <2 seconds (100x faster)
```

**Step 5: Rollback Testing**
```bash
# Test that rollback works
python -m alembic downgrade add_missing_indexes_003

# Verify tables reverted
python inspect_migration_state.py
# Should show: user_id columns gone, id column empty

# Re-apply migration
python -m alembic upgrade normalize_user_ids_004
```

**Step 6: Full Pipeline Test**
```bash
# Run complete pipeline with migrated schema
python main.py

# Verify:
- harvest_sqlite completes without errors
- report_sqlite completes within expected time
- Dashboard JSON exported correctly
- No data corruption or missing records
```

**Step 7: Load Testing (Optional)**
```bash
# Create larger test dataset if available
# Test with 1000+ members
# Verify memory usage stays reasonable
# Check query times under load
```

ROLLBACK PLAN (If Issues Found):
================================================================

**Immediate Rollback:**
```bash
# Step 1: Stop all running processes
pkill -f main.py

# Step 2: Restore from pre-migration backup
cp backups/clan_data_YYYYMMDD_HHMMSS.db clan_data.db

# Step 3: Verify restoration
pytest tests/test_database_integrity.py -v
```

**Partial Rollback (If only final migration fails):**
```bash
python -m alembic downgrade normalize_user_ids_004
# Keeps drop_unused_001 and add_missing_indexes_003 in place
```

DEPLOYMENT CHECKLIST:
================================================================

- [ ] All 5 migrations created and tested
- [ ] All 41 tests passing (26 username + 9 harvest + 6 integrity)
- [ ] Staging test completed successfully
- [ ] Data integrity validated on production DB
- [ ] Performance improvement confirmed (if using new queries)
- [ ] Rollback tested and documented
- [ ] No regressions found
- [ ] Team notified of schema changes
- [ ] Maintenance window scheduled
- [ ] Backup created before production deployment

MONITORING POST-DEPLOYMENT:
================================================================

After deploying to production:

1. **Monitor database size:** Should remain ~1.1 GB (not growing unexpectedly)
2. **Monitor query performance:** New ID-based queries should be faster
3. **Monitor error logs:** Check for any FK constraint violations
4. **Monitor FK relationship integrity:** Verify no orphaned records

If issues found:
- Use rollback plan above
- Document issue in IMPLEMENTATION_PROGRESS.md
- Create GitHub issue for tracking

SUPPORT CONTACTS:
================================================================

For issues during staging/production deployment:
1. Check IMPLEMENTATION_PROGRESS.md for current status
2. Review migration files in alembic/versions/
3. Check database backup integrity
4. Consult migration_helper.py for safe recovery

================================================================

This test plan ensures all migrations work correctly before 
affecting the production database.
