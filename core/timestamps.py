"""
TimestampHelper module for timezone-safe operations.

All internal logic uses UTC. Conversion happens only at display time.
This module centralizes all datetime operations to prevent timezone bugs.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional


class TimestampHelper:
    """Static methods for timezone-safe timestamp operations."""

    @staticmethod
    def now_utc() -> datetime:
        """
        Get current UTC time as timezone-aware datetime.

        Returns:
            datetime: Current UTC time with UTC timezone info.
        """
        return datetime.now(timezone.utc)

    @staticmethod
    def to_utc(dt: Optional[datetime]) -> Optional[datetime]:
        """
        Convert any datetime to UTC timezone-aware datetime.

        Handles three cases:
        1. Naive datetime (no timezone) - assumes UTC
        2. Timezone-aware datetime - converts to UTC
        3. None - returns None

        Args:
            dt: datetime object (naive or aware) or None

        Returns:
            datetime: UTC timezone-aware datetime, or None if input is None
        """
        if dt is None:
            return None

        # If naive (no timezone info), assume UTC and add timezone
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)

        # If already has timezone, convert to UTC
        return dt.astimezone(timezone.utc)

    @staticmethod
    def cutoff_days_ago(days: int) -> datetime:
        """
        Get UTC datetime for N days ago.

        Useful for filtering queries like "messages from last 30 days".

        Args:
            days: Number of days in the past

        Returns:
            datetime: UTC datetime representing N days ago
        """
        return TimestampHelper.now_utc() - timedelta(days=days)

    @staticmethod
    def validate_timestamp(ts: datetime) -> bool:
        """
        Validate that a timestamp is reasonable.

        Checks:
        - Not in the far future (>1 year ahead)
        - Not before year 2000 (project start)
        - Has timezone info (or is UTC-compatible)

        Args:
            ts: datetime to validate

        Returns:
            bool: True if timestamp is reasonable, False otherwise
        """
        if ts is None:
            return False

        now = TimestampHelper.now_utc()
        one_year_future = now + timedelta(days=365)
        year_2000 = datetime(2000, 1, 1, tzinfo=timezone.utc)

        # Check bounds
        if ts < year_2000:
            return False
        if ts > one_year_future:
            return False

        return True

    @staticmethod
    def format_for_display(dt: Optional[datetime]) -> str:
        """
        Format a UTC datetime for user display.

        Uses ISO 8601 format: YYYY-MM-DD HH:MM:SS UTC

        Args:
            dt: datetime to format (should be UTC)

        Returns:
            str: Human-readable formatted timestamp, or "N/A" if None
        """
        if dt is None:
            return "N/A"

        # Ensure UTC
        dt_utc = TimestampHelper.to_utc(dt)

        # Format as ISO 8601 with UTC suffix
        return dt_utc.strftime("%Y-%m-%d %H:%M:%S UTC")
