"""
Tests for TimestampHelper module.

Covers:
- now_utc() - current UTC time
- to_utc() - conversion of naive/aware datetimes and None
- cutoff_days_ago() - cutoff calculation
- validate_timestamp() - validation bounds
- format_for_display() - display formatting
"""

import pytest
from datetime import datetime, timedelta, timezone
from core.timestamps import TimestampHelper


class TestNowUTC:
    """Tests for TimestampHelper.now_utc()."""

    def test_now_utc_returns_datetime(self):
        """now_utc() should return a datetime object."""
        result = TimestampHelper.now_utc()
        assert isinstance(result, datetime)

    def test_now_utc_is_timezone_aware(self):
        """now_utc() should return timezone-aware datetime."""
        result = TimestampHelper.now_utc()
        assert result.tzinfo is not None
        assert result.tzinfo == timezone.utc

    def test_now_utc_is_recent(self):
        """now_utc() should return a recent time (within last second)."""
        before = datetime.now(timezone.utc)
        result = TimestampHelper.now_utc()
        after = datetime.now(timezone.utc)
        
        # Should be between before and after
        assert before <= result <= after


class TestToUTC:
    """Tests for TimestampHelper.to_utc()."""

    def test_to_utc_with_none(self):
        """to_utc(None) should return None."""
        result = TimestampHelper.to_utc(None)
        assert result is None

    def test_to_utc_naive_datetime(self):
        """to_utc() should add UTC timezone to naive datetime."""
        naive_dt = datetime(2025, 12, 22, 10, 30, 0)
        result = TimestampHelper.to_utc(naive_dt)
        
        assert result.year == 2025
        assert result.month == 12
        assert result.day == 22
        assert result.hour == 10
        assert result.minute == 30
        assert result.tzinfo == timezone.utc

    def test_to_utc_aware_utc_datetime(self):
        """to_utc() should return UTC datetime unchanged."""
        utc_dt = datetime(2025, 12, 22, 10, 30, 0, tzinfo=timezone.utc)
        result = TimestampHelper.to_utc(utc_dt)
        
        assert result == utc_dt
        assert result.tzinfo == timezone.utc

    def test_to_utc_aware_non_utc_datetime(self):
        """to_utc() should convert non-UTC aware datetime to UTC."""
        # Create a datetime 5 hours ahead of UTC
        five_hours_ahead = timezone(timedelta(hours=5))
        dt_ahead = datetime(2025, 12, 22, 15, 30, 0, tzinfo=five_hours_ahead)
        
        result = TimestampHelper.to_utc(dt_ahead)
        
        # Should have converted to UTC
        assert result.tzinfo == timezone.utc
        # Original was 15:30+05:00, so in UTC it's 10:30
        assert result.hour == 10
        assert result.minute == 30

    def test_to_utc_preserves_actual_moment(self):
        """to_utc() should preserve the actual moment in time."""
        # 12:00 UTC+3 = 09:00 UTC
        tz_plus_3 = timezone(timedelta(hours=3))
        dt_plus_3 = datetime(2025, 12, 22, 12, 0, 0, tzinfo=tz_plus_3)
        
        result = TimestampHelper.to_utc(dt_plus_3)
        expected = datetime(2025, 12, 22, 9, 0, 0, tzinfo=timezone.utc)
        
        assert result == expected


class TestCutoffDaysAgo:
    """Tests for TimestampHelper.cutoff_days_ago()."""

    def test_cutoff_zero_days(self):
        """cutoff_days_ago(0) should return approximately now."""
        before = TimestampHelper.now_utc()
        result = TimestampHelper.cutoff_days_ago(0)
        after = TimestampHelper.now_utc()
        
        # Should be very close to now (within 1 second)
        assert before <= result <= after

    def test_cutoff_positive_days(self):
        """cutoff_days_ago(N) should return N days in the past."""
        days = 7
        result = TimestampHelper.cutoff_days_ago(days)
        
        # Calculate expected cutoff
        now = TimestampHelper.now_utc()
        expected_approx = now - timedelta(days=days)
        
        # Should be within 1 second of expected
        diff = abs((result - expected_approx).total_seconds())
        assert diff < 1

    def test_cutoff_returns_utc(self):
        """cutoff_days_ago() should return UTC timezone-aware datetime."""
        result = TimestampHelper.cutoff_days_ago(30)
        assert result.tzinfo == timezone.utc

    def test_cutoff_respects_exact_days(self):
        """cutoff_days_ago() should calculate days correctly."""
        result = TimestampHelper.cutoff_days_ago(1)
        now = TimestampHelper.now_utc()
        
        # Difference should be approximately 1 day
        diff_hours = (now - result).total_seconds() / 3600
        assert 23.5 < diff_hours < 24.5


class TestValidateTimestamp:
    """Tests for TimestampHelper.validate_timestamp()."""

    def test_validate_none_returns_false(self):
        """validate_timestamp(None) should return False."""
        result = TimestampHelper.validate_timestamp(None)
        assert result is False

    def test_validate_current_time_returns_true(self):
        """validate_timestamp() should accept current UTC time."""
        now = TimestampHelper.now_utc()
        result = TimestampHelper.validate_timestamp(now)
        assert result is True

    def test_validate_recent_past_returns_true(self):
        """validate_timestamp() should accept recent past dates."""
        past = TimestampHelper.now_utc() - timedelta(days=30)
        result = TimestampHelper.validate_timestamp(past)
        assert result is True

    def test_validate_far_future_returns_false(self):
        """validate_timestamp() should reject far future (>1 year)."""
        far_future = TimestampHelper.now_utc() + timedelta(days=400)
        result = TimestampHelper.validate_timestamp(far_future)
        assert result is False

    def test_validate_near_future_returns_true(self):
        """validate_timestamp() should accept near future (<1 year)."""
        near_future = TimestampHelper.now_utc() + timedelta(days=100)
        result = TimestampHelper.validate_timestamp(near_future)
        assert result is True

    def test_validate_year_2000_returns_true(self):
        """validate_timestamp() should accept year 2000 (boundary)."""
        y2k = datetime(2000, 1, 1, tzinfo=timezone.utc)
        result = TimestampHelper.validate_timestamp(y2k)
        assert result is True

    def test_validate_before_year_2000_returns_false(self):
        """validate_timestamp() should reject dates before 2000."""
        pre_2000 = datetime(1999, 12, 31, tzinfo=timezone.utc)
        result = TimestampHelper.validate_timestamp(pre_2000)
        assert result is False

    def test_validate_old_date_returns_false(self):
        """validate_timestamp() should reject dates far in past."""
        old = datetime(1970, 1, 1, tzinfo=timezone.utc)
        result = TimestampHelper.validate_timestamp(old)
        assert result is False


class TestFormatForDisplay:
    """Tests for TimestampHelper.format_for_display()."""

    def test_format_none_returns_na(self):
        """format_for_display(None) should return 'N/A'."""
        result = TimestampHelper.format_for_display(None)
        assert result == "N/A"

    def test_format_utc_datetime(self):
        """format_for_display() should format UTC datetime correctly."""
        dt = datetime(2025, 12, 22, 10, 30, 45, tzinfo=timezone.utc)
        result = TimestampHelper.format_for_display(dt)
        
        assert result == "2025-12-22 10:30:45 UTC"

    def test_format_naive_datetime(self):
        """format_for_display() should handle naive datetime (assume UTC)."""
        naive_dt = datetime(2025, 12, 22, 10, 30, 45)
        result = TimestampHelper.format_for_display(naive_dt)
        
        # Should add UTC and format
        assert "2025-12-22 10:30:45 UTC" == result

    def test_format_non_utc_aware_datetime(self):
        """format_for_display() should convert non-UTC aware to UTC."""
        tz_plus_2 = timezone(timedelta(hours=2))
        dt_plus_2 = datetime(2025, 12, 22, 12, 0, 0, tzinfo=tz_plus_2)
        
        result = TimestampHelper.format_for_display(dt_plus_2)
        
        # Should be converted to UTC (12:00+02:00 = 10:00 UTC)
        assert "2025-12-22 10:00:00 UTC" == result

    def test_format_contains_utc_suffix(self):
        """format_for_display() output should always contain 'UTC'."""
        dt = datetime(2025, 12, 22, 10, 30, 0, tzinfo=timezone.utc)
        result = TimestampHelper.format_for_display(dt)
        
        assert "UTC" in result

    def test_format_iso_8601_compatible(self):
        """format_for_display() should use ISO 8601 format."""
        dt = datetime(2025, 1, 5, 9, 5, 3, tzinfo=timezone.utc)
        result = TimestampHelper.format_for_display(dt)
        
        # Check ISO format: YYYY-MM-DD HH:MM:SS UTC
        assert result == "2025-01-05 09:05:03 UTC"


class TestIntegration:
    """Integration tests combining multiple methods."""

    def test_to_utc_then_format(self):
        """Should be able to convert naive datetime and format."""
        naive_dt = datetime(2025, 12, 22, 10, 30, 0)
        utc_dt = TimestampHelper.to_utc(naive_dt)
        formatted = TimestampHelper.format_for_display(utc_dt)
        
        assert formatted == "2025-12-22 10:30:00 UTC"

    def test_cutoff_plus_validation(self):
        """Cutoff dates should always validate."""
        cutoff = TimestampHelper.cutoff_days_ago(30)
        is_valid = TimestampHelper.validate_timestamp(cutoff)
        
        assert is_valid is True

    def test_now_plus_validation(self):
        """Current time should always validate."""
        now = TimestampHelper.now_utc()
        is_valid = TimestampHelper.validate_timestamp(now)
        
        assert is_valid is True

    def test_full_workflow_discord_message(self):
        """Full workflow: receive discord timestamp, store as UTC, display."""
        # Simulate Discord API response (timezone-aware)
        discord_tz = timezone(timedelta(hours=0))  # Discord uses UTC
        discord_ts = datetime(2025, 12, 22, 15, 30, 0, tzinfo=discord_tz)
        
        # Convert to our UTC
        stored_ts = TimestampHelper.to_utc(discord_ts)
        assert stored_ts.tzinfo == timezone.utc
        
        # Validate it
        is_valid = TimestampHelper.validate_timestamp(stored_ts)
        assert is_valid is True
        
        # Display to user
        displayed = TimestampHelper.format_for_display(stored_ts)
        assert "UTC" in displayed
        assert "2025-12-22" in displayed
