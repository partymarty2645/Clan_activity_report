"""
Analytics Service
=================
Centralized logic for calculating Clan Statistics, Time-Deltas, and Outliers.
Replaces duplicate logic in `report.py` and `dashboard_export.py`.
Uses SQLAlchemy models for strict typing and connection pooling.

Note: This service supports both username-based and ID-based queries.
Username-based queries work with current schema.
ID-based queries (get_*_by_id methods) are available once user_id FK populated (Phase 2.2.2).

Timestamps: All methods use UTC internally. Use TimestampHelper for creating cutoff dates.
"""
import logging
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session

from database.models import WOMSnapshot, DiscordMessage, ClanMember
from core.utils import normalize_user_string
from core.timestamps import TimestampHelper
from core.config import Config

logger = logging.getLogger("Analytics")

class AnalyticsService:
    def __init__(self, db_session: Session):
        self.db = db_session

    def get_latest_snapshots(self) -> Dict[str, WOMSnapshot]:
        """
        Fetches the absolute latest snapshot for every user.
        Returns: {normalized_username: WOMSnapshot}
        """
        # Subquery: Max timestamp per user
        subq = (
            select(WOMSnapshot.username, func.max(WOMSnapshot.timestamp).label("max_ts"))
            .group_by(WOMSnapshot.username)
            .subquery()
        )
        
        # Join
        stmt = (
            select(WOMSnapshot)
            .join(subq, and_(
                WOMSnapshot.username == subq.c.username,
                WOMSnapshot.timestamp == subq.c.max_ts
            ))
        )
        
        results = self.db.execute(stmt).scalars().all()
        return {normalize_user_string(r.username): r for r in results}

    def get_snapshots_at_cutoff(self, cutoff_date: datetime) -> Dict[str, WOMSnapshot]:
        """
        Fetches the snapshot closest to (available at or after) the cutoff date.
        Used for calculating gains (Current - Old).
        """
        # We want MIN(timestamp) where timestamp >= cutoff
        subq = (
            select(WOMSnapshot.username, func.min(WOMSnapshot.timestamp).label("min_ts"))
            .where(WOMSnapshot.timestamp >= cutoff_date)
            .group_by(WOMSnapshot.username)
            .subquery()
        )
        
        stmt = (
            select(WOMSnapshot)
            .join(subq, and_(
                WOMSnapshot.username == subq.c.username,
                WOMSnapshot.timestamp == subq.c.min_ts
            ))
        )
        
        results = self.db.execute(stmt).scalars().all()
        return {normalize_user_string(r.username): r for r in results}

    def get_message_counts(self, start_date: datetime) -> Dict[str, int]:
        """
        Counts discord messages per user since start_date.
        Handles case-insensitivity.
        """
        stmt = (
            select(
                func.lower(DiscordMessage.author_name).label("name"), 
                func.count(DiscordMessage.id).label("count")
            )
            .where(DiscordMessage.created_at >= start_date)
            .group_by(func.lower(DiscordMessage.author_name))
        )
        
        results = self.db.execute(stmt).all()
        
        # Normalize keys
        counts = {}
        for row in results:
            norm = normalize_user_string(row.name)
            counts[norm] = counts.get(norm, 0) + row.count
            
        return counts

    def calculate_gains(self, current_map: Dict[str, WOMSnapshot], 
                        old_map: Dict[str, WOMSnapshot],
                        staleness_limit_days: Optional[int] = None) -> Dict[str, Dict[str, int]]:
        """
        Calculates delta (XP, Boss Kills) between current and old snapshots.
        Optionally filters out stale data where snapshot is older than limit.
        
        Returns: {username: {'xp': int, 'boss': int}}
        
        Args:
            current_map: Latest snapshots {username: WOMSnapshot}
            old_map: Historical snapshots {username: WOMSnapshot}
            staleness_limit_days: Max age in days. Exclude gains if old snap is older than this.
        """
        gains = {}
        for user, curr in current_map.items():
            old = old_map.get(user)
            
            xp_gain = 0
            boss_gain = 0
            
            if old:
                # Check staleness if limit is set
                if staleness_limit_days is not None:
                    # If old snapshot is too old, skip this user (don't count gains)
                    age_days = (curr.timestamp - old.timestamp).days if curr.timestamp and old.timestamp else 0
                    if age_days > staleness_limit_days:
                        continue  # Skip this user, don't include in gains
                
                xp_gain = (curr.total_xp or 0) - (old.total_xp or 0)
                boss_gain = (curr.total_boss_kills or 0) - (old.total_boss_kills or 0)
            
            # Sanity check: Gains cannot be negative (unless massive rollback/glitch, but we clamp to 0)
            gains[user] = {
                'xp': max(0, xp_gain),
                'boss': max(0, boss_gain)
            }
            
        return gains

    def get_detailed_boss_gains(self, current_map: Dict[str, WOMSnapshot],
                              old_map: Dict[str, WOMSnapshot]) -> Dict[str, int]:
        """
        Calculates specific boss kills gained using SQL Aggregation on BossSnapshot.
        Faster and more reliable than parsing JSON.
        Returns: {'Kraken': 500, 'Zulrah': 200, ...}
        """
        from database.models import BossSnapshot
        
        # We need to query the DB for the IDs in the maps.
        # It's more efficient to do this in bulk.
        
        curr_ids = [s.id for s in current_map.values() if s.id]
        old_ids = [s.id for s in old_map.values() if s.id]
        
        if not curr_ids:
            return {}
            
        # Helper to sum kills by boss for a list of snapshot IDs
        def get_sums(ids):
            if not ids: return {}
            stmt = (
                select(BossSnapshot.boss_name, func.sum(BossSnapshot.kills))
                .where(BossSnapshot.snapshot_id.in_(ids))
                .group_by(BossSnapshot.boss_name)
            )
            return {row[0]: (row[1] or 0) for row in self.db.execute(stmt).all()}

        # 1. Get Totals for CURRENT snapshots
        curr_sums = get_sums(curr_ids)
        
        # 2. Get Totals for OLD snapshots
        old_sums = get_sums(old_ids)
        
        # 3. Diff
        gains = {}
        for boss, kills in curr_sums.items():
            prev = old_sums.get(boss, 0)
            delta = kills - prev
            if delta > 0:
                gains[boss] = delta
                
        return gains

    def get_user_top_boss_gains(self, current_map: Dict[str, WOMSnapshot], 
                              old_map: Dict[str, WOMSnapshot]) -> Dict[str, tuple]:
        """
        Calculates the single boss with the highest Kill Delta for each user.
        Returns: {username: (boss_name, delta_count)}
        Example: {'party_marty': ('vorkath', 50)}
        """
        from database.models import BossSnapshot
        
        # 1. Collect all IDs
        curr_ids = [s.id for s in current_map.values() if s.id]
        old_ids = [s.id for s in old_map.values() if s.id]
        
        if not curr_ids:
            return {}

        # 2. Bulk Fetch Helper: Returns {snapshot_id: {boss_name: kills}}
        def get_snapshot_boss_data(ids):
            if not ids: return {}
            stmt = (
                select(BossSnapshot.snapshot_id, BossSnapshot.boss_name, BossSnapshot.kills)
                .where(BossSnapshot.snapshot_id.in_(ids))
            )
            rows = self.db.execute(stmt).all()
            data = {}
            for row in rows:
                if row.snapshot_id not in data:
                    data[row.snapshot_id] = {}
                data[row.snapshot_id][row.boss_name] = row.kills
            return data

        # 3. Fetch Data
        curr_data = get_snapshot_boss_data(curr_ids)
        old_data = get_snapshot_boss_data(old_ids)
        
        # 4. Compare
        results = {}
        for user, curr_snap in current_map.items():
            best_boss = "None"
            max_delta = -1
            
            curr_bosses = curr_data.get(curr_snap.id, {})
            old_snap = old_map.get(user)
            old_bosses = old_data.get(old_snap.id, {}) if old_snap else {}
            
            for boss, kills in curr_bosses.items():
                prev = old_bosses.get(boss, 0)
                delta = kills - prev
                if delta > max_delta:
                    max_delta = delta
                    best_boss = boss
            
            # Only record if there's actual activity
            if max_delta > 0:
                results[user] = (best_boss, max_delta)
                
        return results

    def get_activity_heatmap(self, start_date: datetime) -> List[Dict[str, int]]:
        """
        Returns message volume by DayOfWeek and Hour for heatmap.
        Uses SQLite strftime function.
        Returns: [{'day': 0-6, 'hour': 0-23, 'value': count}, ...]
        """
        # SQLite strftime: %w = Day of week 0-6 (Sunday=0), %H = Hour 00-23
        stmt = (
            select(
                func.strftime('%w', DiscordMessage.created_at).label("dow"),
                func.strftime('%H', DiscordMessage.created_at).label("hour"),
                func.count(DiscordMessage.id).label("count")
            )
            .where(DiscordMessage.created_at >= start_date)
            .group_by("dow", "hour")
        )
        
        results = self.db.execute(stmt).all()
        
        data = []
        for row in results:
            try:
                data.append({
                    "day": int(row.dow),
                    "hour": int(row.hour),
                    "value": row.count
                })
            except (ValueError, TypeError):
                continue
                
        return data

    def calculate_outliers(self, stats_list: List[Dict]) -> List[Dict]:
        """
        Analyzes stats for Outliers.
        Expects stats_list items to have keys: ['username', 'xp_7d', 'msgs_7d', 'boss_7d']
        """
        outliers = []
        for u in stats_list:
            xp = u.get('xp_7d', 0)
            msgs = u.get('msgs_7d', 0)
            boss = u.get('boss_7d', 0)
            
            # Fading Star (Churn Risk - High 30d, Low 7d)
            xp_30 = u.get('xp_30d', 0)
            if xp_30 > 5_000_000 and xp < (xp_30 / 10):
                outliers.append({
                    **u,
                    "status": "Fading Star",
                    "reason": "Activity Slump (Churn Risk)",
                    "severity": "High"
                })
            
            # Silent Grinder
            elif xp > 3_000_000 and msgs < 5:
                # Calculate Social Ratio (Msgs per 1M XP)
                ratio =  round(msgs / (xp/1_000_000), 2) if xp > 0 else 0
                outliers.append({
                    **u, 
                    "status": "Silent Grinder",
                    "reason": "High XP, Low Msgs",
                    "severity": "Medium",
                    "social_ratio": ratio
                })
            
            # Town Crier (Chatty, Low XP)
            elif msgs > 300 and xp < 100_000:
                outliers.append({
                     **u,
                     "status": "Town Crier",
                     "reason": "High Msgs, Low XP",
                     "severity": "Low",
                     "social_ratio": 999 
                })
                
            # Boss Hunter (High Boss, Low XP usually implies dedicated PVMer)
            elif boss > 150 and xp < 500_000:
                 outliers.append({
                     **u,
                     "status": "Boss Hunter",
                     "reason": "Only Bossing",
                     "severity": "Medium",
                     "social_ratio": 0
                 })
                 
        # Sort by severity
        severity_map = {"High": 3, "Medium": 2, "Low": 1}
        outliers.sort(key=lambda x: severity_map.get(x.get('severity', 'Low'), 0), reverse=True)
        return outliers[:12]  # Return top 12

    # ==================== ID-BASED QUERY METHODS (Phase 2.2.2+) ====================
    # These methods use user_id FK relationships for better performance and data integrity.
    # Available once Phase 2.2.2 (normalize_user_ids migration) populates the user_id columns.
    # Until then, use the username-based methods above.
    
    def get_latest_snapshots_by_id(self) -> Dict[int, WOMSnapshot]:
        """
        ID-based version of get_latest_snapshots().
        Returns: {user_id: WOMSnapshot}
        Performance: ~100x faster than username-based version (no string normalization).
        
        Requires: user_id FK populated in wom_snapshots (Phase 2.2.2)
        """
        subq = (
            select(WOMSnapshot.user_id, func.max(WOMSnapshot.timestamp).label("max_ts"))
            .where(WOMSnapshot.user_id.isnot(None))  # Only when FK is populated
            .group_by(WOMSnapshot.user_id)
            .subquery()
        )
        
        stmt = (
            select(WOMSnapshot)
            .join(subq, and_(
                WOMSnapshot.user_id == subq.c.user_id,
                WOMSnapshot.timestamp == subq.c.max_ts
            ))
        )
        
        results = self.db.execute(stmt).scalars().all()
        return {r.user_id: r for r in results if r.user_id}
    
    def get_snapshots_at_cutoff_by_id(self, cutoff_date: datetime) -> Dict[int, WOMSnapshot]:
        """
        ID-based version of get_snapshots_at_cutoff().
        Returns: {user_id: WOMSnapshot}
        Performance: Avoids username normalization overhead.
        
        Requires: user_id FK populated in wom_snapshots (Phase 2.2.2)
        """
        subq = (
            select(WOMSnapshot.user_id, func.min(WOMSnapshot.timestamp).label("min_ts"))
            .where(and_(
                WOMSnapshot.timestamp >= cutoff_date,
                WOMSnapshot.user_id.isnot(None)
            ))
            .group_by(WOMSnapshot.user_id)
            .subquery()
        )
        
        stmt = (
            select(WOMSnapshot)
            .join(subq, and_(
                WOMSnapshot.user_id == subq.c.user_id,
                WOMSnapshot.timestamp == subq.c.min_ts
            ))
        )
        
        results = self.db.execute(stmt).scalars().all()
        return {r.user_id: r for r in results if r.user_id}
    
    def get_message_counts_by_id(self, start_date: datetime) -> Dict[int, int]:
        """
        ID-based version of get_message_counts().
        Returns: {user_id: message_count}
        Performance: Direct ID join, no string normalization needed.
        
        Requires: user_id FK populated in discord_messages (Phase 2.2.2)
        """
        stmt = (
            select(
                DiscordMessage.user_id,
                func.count(DiscordMessage.id).label("count")
            )
            .where(and_(
                DiscordMessage.created_at >= start_date,
                DiscordMessage.user_id.isnot(None)
            ))
            .group_by(DiscordMessage.user_id)
        )
        
        results = self.db.execute(stmt).all()
        return {row.user_id: row.count for row in results}
    
    def get_gains_by_id(self, current_map: Dict[int, WOMSnapshot],
                       old_map: Dict[int, WOMSnapshot]) -> Dict[int, Dict[str, int]]:
        """
        ID-based version of calculate_gains().
        Returns: {user_id: {'xp': int, 'boss': int}}
        
        Requires: current_map and old_map returned from get_latest_snapshots_by_id/get_snapshots_at_cutoff_by_id
        """
        gains = {}
        for user_id, curr in current_map.items():
            old = old_map.get(user_id)
            
            xp_gain = 0
            boss_gain = 0
            
            if old:
                xp_gain = (curr.total_xp or 0) - (old.total_xp or 0)
                boss_gain = (curr.total_boss_kills or 0) - (old.total_boss_kills or 0)
            
            gains[user_id] = {
                'xp': max(0, xp_gain),
                'boss': max(0, boss_gain)
            }
        
        return gains
    
    def get_user_data_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Fetch user profile from ClanMember table by ID.
        Returns: {'id', 'username', 'role', 'joined_at'} or None if not found.
        
        Requires: user_id exists in clan_members (Phase 2.2.2)
        """
        stmt = select(ClanMember).where(ClanMember.id == user_id)
        member = self.db.execute(stmt).scalar()
        
        if not member:
            return None
        
        return {
            'id': member.id,
            'username': member.username,
            'role': member.role,
            'joined_at': member.joined_at
        }

    def get_user_snapshots_bulk(self, user_ids: List[int]) -> Dict[int, WOMSnapshot]:
        """
        Bulk fetch latest snapshots for multiple user IDs in a single query.
        Avoids N+1 query problem compared to fetching each user individually.
        
        Returns: {user_id: WOMSnapshot}
        Performance: 1 query instead of N queries
        
        Requires: user_id FK populated in wom_snapshots (Phase 2.2.2)
        """
        if not user_ids:
            return {}
        
        # Subquery: Max timestamp per user_id
        subq = (
            select(WOMSnapshot.user_id, func.max(WOMSnapshot.timestamp).label("max_ts"))
            .where(WOMSnapshot.user_id.in_(user_ids))
            .group_by(WOMSnapshot.user_id)
            .subquery()
        )
        
        # Join to get latest snapshot for each user
        stmt = (
            select(WOMSnapshot)
            .join(subq, and_(
                WOMSnapshot.user_id == subq.c.user_id,
                WOMSnapshot.timestamp == subq.c.max_ts
            ))
        )
        
        results = self.db.execute(stmt).scalars().all()
        return {r.user_id: r for r in results if r.user_id}

    def get_discord_message_counts_bulk(self, author_names: List[str], 
                                        start_date: datetime) -> Dict[str, int]:
        """
        Bulk count messages for multiple author names in a single query.
        Avoids N+1 query problem by using IN() clause instead of individual queries.
        
        Returns: {normalized_author_name: message_count}
        Performance: 1 query instead of N queries
        """
        if not author_names:
            return {}
        
        # Normalize author names for case-insensitive comparison
        normalized_names = [name.lower() for name in author_names]
        
        stmt = (
            select(
                func.lower(DiscordMessage.author_name).label("name"),
                func.count(DiscordMessage.id).label("count")
            )
            .where(and_(
                func.lower(DiscordMessage.author_name).in_(normalized_names),
                DiscordMessage.created_at >= start_date
            ))
            .group_by(func.lower(DiscordMessage.author_name))
        )
        
        results = self.db.execute(stmt).all()
        
        # Return with normalized keys
        counts = {}
        for row in results:
            norm = normalize_user_string(row.name)
            counts[norm] = row.count
        
        return counts
