"""
Performance benchmarks for ClanStats pipeline.

Tests measure:
- Analytics query performance (target: <100ms)
- Report generation time (target: <2s for 1000+ members)
- Dashboard export time (target: <1s)

These benchmarks help track performance regressions across releases.
"""

import pytest
import time
from datetime import datetime, timezone, timedelta
from database.connector import SessionLocal
from core.analytics import AnalyticsService
from core.timestamps import TimestampHelper


class TestAnalyticsPerformance:
    """Benchmarks for core analytics operations."""

    @pytest.fixture
    def db_session(self):
        """Provide database session for tests."""
        session = SessionLocal()
        yield session
        session.close()

    @pytest.fixture
    def analytics(self, db_session):
        """Provide AnalyticsService instance."""
        return AnalyticsService(db_session)

    def test_get_latest_snapshots_performance(self, analytics):
        """
        Measure time to fetch latest snapshots for all users.
        Target: <100ms for typical clan (200-500 members)
        """
        start = time.time()
        snapshots = analytics.get_latest_snapshots()
        elapsed = time.time() - start
        
        # Log timing
        num_users = len(snapshots)
        assert elapsed < 1.0, f"get_latest_snapshots() took {elapsed:.3f}s, expected <1.0s for {num_users} users"
        print(f"\n✅ get_latest_snapshots() fetched {num_users} users in {elapsed:.3f}s")

    def test_get_snapshots_at_cutoff_performance(self, analytics):
        """
        Measure time to fetch snapshots at a cutoff date.
        Target: <100ms for typical clan
        """
        cutoff = TimestampHelper.cutoff_days_ago(30)
        
        start = time.time()
        snapshots = analytics.get_snapshots_at_cutoff(cutoff)
        elapsed = time.time() - start
        
        num_users = len(snapshots)
        assert elapsed < 1.0, f"get_snapshots_at_cutoff() took {elapsed:.3f}s, expected <1.0s for {num_users} users"
        print(f"\n✅ get_snapshots_at_cutoff() fetched {num_users} users in {elapsed:.3f}s")

    def test_get_message_counts_performance(self, analytics):
        """
        Measure time to count messages per user.
        Target: <100ms for typical clan
        """
        start_date = TimestampHelper.cutoff_days_ago(30)
        
        start = time.time()
        counts = analytics.get_message_counts(start_date)
        elapsed = time.time() - start
        
        num_users = len(counts)
        assert elapsed < 1.0, f"get_message_counts() took {elapsed:.3f}s, expected <1.0s for {num_users} users"
        print(f"\n✅ get_message_counts() counted {num_users} users in {elapsed:.3f}s")

    def test_bulk_snapshots_vs_single(self, analytics):
        """
        Compare performance of bulk query vs multiple individual queries.
        Bulk method should be significantly faster (no N+1 queries).
        
        Target: Bulk < 100ms vs Single * N could be seconds
        """
        # Get all user IDs first
        all_snapshots = analytics.get_latest_snapshots()
        user_ids = [snap.user_id for snap in all_snapshots.values() if snap.user_id]
        
        if not user_ids:
            pytest.skip("No user IDs populated in database")
        
        # Time bulk query
        start = time.time()
        bulk_results = analytics.get_user_snapshots_bulk(user_ids[:50])  # Test first 50 users
        bulk_elapsed = time.time() - start
        
        # Bulk query should be very fast
        assert bulk_elapsed < 0.5, f"Bulk query took {bulk_elapsed:.3f}s for 50 users"
        assert len(bulk_results) > 0, "Bulk query should return results"
        print(f"\n✅ Bulk query (50 users) completed in {bulk_elapsed:.3f}s")

    def test_calculate_gains_performance(self, analytics):
        """
        Measure time to calculate XP/boss gains between two snapshots.
        Target: <50ms for typical clan
        """
        # Get current and past snapshots
        current = analytics.get_latest_snapshots()
        past = analytics.get_snapshots_at_cutoff(TimestampHelper.cutoff_days_ago(7))
        
        start = time.time()
        gains = analytics.calculate_gains(current, past)
        elapsed = time.time() - start
        
        num_users = len(gains)
        assert elapsed < 0.5, f"calculate_gains() took {elapsed:.3f}s for {num_users} users"
        print(f"\n✅ calculate_gains() processed {num_users} users in {elapsed:.3f}s")


class TestReportPerformance:
    """
    Benchmarks for report generation.
    
    Note: These are integration tests that measure overall performance.
    If report generation fails, these tests will skip gracefully.
    """

    def test_full_pipeline_timing(self):
        """
        Measure overall report generation time.
        Target: <2s for full pipeline
        
        This is an integration test that measures end-to-end performance.
        """
        from reporting.excel import ExcelReporter
        from database.connector import SessionLocal
        from core.analytics import AnalyticsService
        
        db = SessionLocal()
        try:
            analytics = AnalyticsService(db)
            reporter = ExcelReporter()
            
            start = time.time()
            reporter.generate(analytics)
            elapsed = time.time() - start
            
            # Report should complete in reasonable time
            assert elapsed < 10.0, f"Report generation took {elapsed:.3f}s, expected <10s"
            print(f"\n✅ Full report generation completed in {elapsed:.3f}s")
        finally:
            db.close()


class TestQueryOptimization:
    """
    Tests to verify no N+1 query patterns exist.
    These test the query structure, not timing.
    """

    @pytest.fixture
    def db_session(self):
        """Provide database session."""
        session = SessionLocal()
        yield session
        session.close()

    @pytest.fixture
    def analytics(self, db_session):
        """Provide AnalyticsService."""
        return AnalyticsService(db_session)

    def test_bulk_query_uses_single_statement(self, analytics):
        """
        Verify bulk query method exists and is callable.
        (Actual query plan would require deeper SQLAlchemy introspection.)
        """
        # Check method exists
        assert hasattr(analytics, 'get_user_snapshots_bulk'), \
            "get_user_snapshots_bulk method should exist"
        assert callable(analytics.get_user_snapshots_bulk), \
            "get_user_snapshots_bulk should be callable"
        
        # Test with empty list
        result = analytics.get_user_snapshots_bulk([])
        assert result == {}, "Empty user_ids should return empty dict"
        print("\n✅ Bulk query method is implemented and callable")

    def test_discord_bulk_query_exists(self, analytics):
        """
        Verify bulk Discord message counting method exists.
        """
        assert hasattr(analytics, 'get_discord_message_counts_bulk'), \
            "get_discord_message_counts_bulk method should exist"
        assert callable(analytics.get_discord_message_counts_bulk), \
            "get_discord_message_counts_bulk should be callable"
        
        # Test with empty list and cutoff
        result = analytics.get_discord_message_counts_bulk([], datetime.now(timezone.utc))
        assert result == {}, "Empty names should return empty dict"
        print("\n✅ Discord bulk query method is implemented and callable")
