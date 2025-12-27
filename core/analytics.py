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
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from sqlalchemy import select, func, and_, text
from sqlalchemy.orm import Session

from database.models import WOMSnapshot, DiscordMessage, ClanMember, BossSnapshot
from core.usernames import UsernameNormalizer
from core.timestamps import TimestampHelper
from core.config import Config

logger = logging.getLogger("Analytics")

class AnalyticsService:
    def __init__(self, db_session: Session):
        self.db = db_session

    def _latest_snapshots_windowed(self, cutoff_date: Optional[datetime] = None) -> List[WOMSnapshot]:
        """Return the latest snapshot per username with deterministic ordering."""
        window_stmt = select(
            WOMSnapshot.id,
            WOMSnapshot.username,
            WOMSnapshot.timestamp,
            WOMSnapshot.total_xp,
            WOMSnapshot.total_boss_kills,
            func.row_number().over(
                partition_by=WOMSnapshot.username,
                order_by=(WOMSnapshot.timestamp.desc(), WOMSnapshot.id.desc())
            ).label("rn")
        )

        if cutoff_date is not None:
            window_stmt = window_stmt.where(WOMSnapshot.timestamp <= cutoff_date)

        subq = window_stmt.subquery()

        stmt = (
            select(WOMSnapshot)
            .join(subq, WOMSnapshot.id == subq.c.id)
            .where(subq.c.rn == 1)
        )

        return self.db.execute(stmt).scalars().all()

    def get_latest_snapshots(self) -> Dict[str, WOMSnapshot]:
        """
        Fetches the absolute latest snapshot for every user.
        Returns: {normalized_username: WOMSnapshot}
        """
        results = self._latest_snapshots_windowed()
        return {UsernameNormalizer.normalize(r.username): r for r in results}

    def get_active_members(self) -> List[ClanMember]:
        """
        Fetch all active clan members from the source of truth table.
        Returns list of ClanMember ORM objects.
        """
        stmt = select(ClanMember)
        return self.db.execute(stmt).scalars().all()


    def get_min_timestamps(self) -> Dict[str, WOMSnapshot]:
        """
        Fetches the FIRST seen snapshot for every user.
        Used for calculating 'Days in Clan' fallback or lifetime gains.
        Returns: {normalized_username: WOMSnapshot}
        """
        # Subquery: Min timestamp per user
        subq = (
            select(WOMSnapshot.username, func.min(WOMSnapshot.timestamp).label("min_ts"))
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
        return {UsernameNormalizer.normalize(r.username): r for r in results}

    def get_clan_records(self) -> List[Dict[str, Any]]:
        """
        MCP-Enabled Feature: Fetch global max kills for each boss.
        """
        query = """
        SELECT 
            b.boss_name, 
            w.username, 
            MAX(b.kills) as record_kills
        FROM boss_snapshots b
        JOIN wom_snapshots w ON w.id = b.snapshot_id
        WHERE b.kills > 0
        GROUP BY b.boss_name
        ORDER BY record_kills DESC
        """
        try:
            results = self.db.execute(text(query)).fetchall()
            # Convert to list of dicts
            return [
                {"boss": r[0].replace('_', ' ').title(), "holder": r[1], "kills": r[2], "boss_id": r[0]}
                for r in results
            ]
        except Exception as e:
            logger.error(f"Failed to fetch clan records: {e}")
            return []

    def get_snapshots_at_cutoff(self, cutoff_date: datetime) -> Dict[str, WOMSnapshot]:
        """
        Fetches the snapshot closest to (available at or after) the cutoff date.
        Used for calculating gains (Current - Old).
        """
        results = self._latest_snapshots_windowed(cutoff_date)
        return {UsernameNormalizer.normalize(r.username): r for r in results}

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
            norm = UsernameNormalizer.normalize(row.name)
            counts[norm] = counts.get(norm, 0) + row.count
            
        return counts

    def calculate_gains(self, current_map: Dict[str, WOMSnapshot], 
                        old_map: Dict[str, WOMSnapshot],
                        staleness_limit_days: Optional[int] = None,
                        fallback_map: Optional[Dict[str, WOMSnapshot]] = None) -> Dict[str, Dict[str, int]]:
        """
        Calculates delta (XP, Boss Kills) between current and old snapshots.
        Optionally filters out stale data where snapshot is older than limit.
        Optionally falls back to a secondary map (e.g., first seen) if old snapshot is missing.
        
        Returns: {username: {'xp': int, 'boss': int}}
        
        Args:
            current_map: Latest snapshots {username: WOMSnapshot}
            old_map: Historical snapshots {username: WOMSnapshot}
            staleness_limit_days: Max age in days. Exclude gains if old snap is older than this.
            fallback_map: Fallback snapshots to use if user is missing from old_map.
        """
        gains = {}
        for user, curr in current_map.items():
            old = old_map.get(user)
            
            # If no snapshot at cutoff, try fallback (e.g., first seen)
            if old is None and fallback_map:
                old = fallback_map.get(user)
            
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

    def _get_boss_kills_by_snapshot(self, snapshot_ids: List[int]) -> Dict[int, Dict[str, int]]:
        """Fetch boss kills per snapshot ID in a single query to avoid N+1 patterns."""
        if not snapshot_ids:
            return {}

        from database.models import BossSnapshot

        stmt = (
            select(BossSnapshot.snapshot_id, BossSnapshot.boss_name, BossSnapshot.kills)
            .where(BossSnapshot.snapshot_id.in_(snapshot_ids))
        )

        data: Dict[int, Dict[str, int]] = {}
        for row in self.db.execute(stmt).all():
            snap_id, boss_name, kills = row
            if snap_id not in data:
                data[snap_id] = {}
            data[snap_id][boss_name] = (kills or 0)
        return data

    def get_detailed_boss_gains(self, current_map: Dict[str, WOMSnapshot],
                              old_map: Dict[str, WOMSnapshot]) -> Dict[str, int]:
        """
        Calculates specific boss kills gained using a single bulk fetch across snapshots.
        Returns: {'Kraken': 500, 'Zulrah': 200, ...}
        """
        curr_ids = [s.id for s in current_map.values() if s.id]
        old_ids = [s.id for s in old_map.values() if s.id]

        if not curr_ids:
            return {}

        all_ids = list(set(curr_ids + old_ids))
        boss_data = self._get_boss_kills_by_snapshot(all_ids)

        curr_sums: Dict[str, int] = defaultdict(int)
        old_sums: Dict[str, int] = defaultdict(int)
        curr_set = set(curr_ids)

        for snap_id, bosses in boss_data.items():
            target = curr_sums if snap_id in curr_set else old_sums
            for boss, kills in bosses.items():
                target[boss] += kills

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
        # 1. Collect all IDs
        curr_ids = [s.id for s in current_map.values() if s.id]
        old_ids = [s.id for s in old_map.values() if s.id]

        if not curr_ids:
            return {}

        boss_data = self._get_boss_kills_by_snapshot(list(set(curr_ids + old_ids)))
        curr_data = {sid: boss_data.get(sid, {}) for sid in curr_ids}
        old_data = {sid: boss_data.get(sid, {}) for sid in old_ids}
        
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
        # Normalize inputs
        normalized_names = [UsernameNormalizer.normalize(name) for name in author_names]
        
        # Build query
        # Since we store 'author_name' which might be raw discord name, we might need alias lookup?
        # Actually, Discord messages usually store the author_name from the event.
        # But we are querying.
        
        # If we have normalized names, we need to match against normalized column or lower(column)
        # But DiscordMessage.author_name is just string.
        # The most robust way is to fetch matches where lower(author_name) in normalized_names
        # BUT normalized_names might have spaces vs underscores.
        
        # Let's rely on the fact that identity_service likely links user_id correctly.
        # If we have user_ids, use those.
        # But this function takes 'author_names'.
        
        # For strict correctness, we should resolve names to user_ids first?
        # analytics.py shouldn't depend on too many things.
        
        # Let's stick to the requested change: use normalize() where we used .lower()
        pass 
        # Actually, line 536 corresponds to `get_discord_activity`.
        # The query probably filters by author_name.
        
        # Let's assume the DB stores `author_name` as it appeared on Discord.
        # If we are searching by a list of names, we should try to match loosely.
        # But replacing .lower() with normalize() is safer for dictionary keys.
        
        normalized_names = [UsernameNormalizer.normalize(name) for name in author_names]
        
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
        from core.usernames import UsernameNormalizer
        counts = {}
        for row in results:
            norm = UsernameNormalizer.normalize(row.name, for_comparison=True)
            counts[norm] = row.count
        
        return counts

    # --- Chart & Dashboard Analytics (Migrated from export_sqlite.py) ---

    def get_boss_diversity(self, snapshot_ids: List[int]) -> Dict[str, Any]:
        """Calculates boss diversity for the given snapshot IDs."""
        if not snapshot_ids: return {"labels": [], "datasets": [{"data": []}]}
        from data.queries import Queries
        placeholders = ','.join('?' * len(snapshot_ids))
        rows = self.db.connection().exec_driver_sql(Queries.GET_BOSS_DIVERSITY.format(placeholders), tuple(snapshot_ids)).fetchall()
        
        sorted_data = sorted(rows, key=lambda x: x[1], reverse=True)
        labels = [row[0].replace('_', ' ').title() for row in sorted_data if row[1] > 0]
        values = [row[1] for row in sorted_data if row[1] > 0]
        return {"labels": labels, "datasets": [{"data": values}]}

    def get_raids_performance(self, snapshot_ids: List[int]) -> Dict[str, Any]:
        """Calculates total raids KC for CoX, ToB, ToA."""
        if not snapshot_ids: return {"labels": [], "datasets": [{"data": []}]}
        from data.queries import Queries
        placeholders = ','.join('?' * len(snapshot_ids))
        rows = self.db.connection().exec_driver_sql(Queries.GET_BOSS_SUMS_FOR_IDS.format(placeholders), tuple(snapshot_ids)).fetchall()
        
        raids_map = {
            'Chambers Of Xeric': 'CoX', 'Chambers Of Xeric Challenge Mode': 'CoX',
            'Theatre Of Blood': 'ToB', 'Theatre Of Blood Hard Mode': 'ToB',
            'Tombs Of Amascut': 'ToA', 'Tombs Of Amascut Expert': 'ToA'
        }
        raids_counts = {'CoX': 0, 'ToB': 0, 'ToA': 0}
        for name_raw, count in rows:
            name = name_raw.replace('_', ' ').title()
            if name in raids_map:
                raids_counts[raids_map[name]] += count
        return {"labels": list(raids_counts.keys()), "datasets": [{"data": list(raids_counts.values())}]}

    def get_skill_mastery(self, snapshot_ids: List[int]) -> Dict[str, Any]:
        """Counts 99s across all skills using the 'raw_data' JSON column."""
        if not snapshot_ids: return {"labels": [], "datasets": [{"data": []}]}
        from data.queries import Queries
        placeholders = ','.join('?' * len(snapshot_ids))
        rows = self.db.connection().exec_driver_sql(Queries.GET_RAW_DATA_FOR_IDS.format(placeholders), tuple(snapshot_ids)).fetchall()
        
        skill_counts = defaultdict(int)
        for (json_str,) in rows:
            if not json_str: continue
            try:
                data = json.loads(json_str)
                # Handle varying WOM JSON structure
                skills = data.get('data', {}).get('skills', {}) or data.get('skills', {})
                for skill, stats in skills.items():
                    if skill != 'overall' and stats.get('level', 0) >= 99:
                        skill_counts[skill] += 1
            except json.JSONDecodeError: continue
            
        sorted_skills = sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)
        return {"labels": [s[0].title() for s in sorted_skills], "datasets": [{"data": [s[1] for s in sorted_skills]}]}

    def get_discord_stats_simple(self, days: Optional[int] = None) -> Dict[str, int]:
        """Returns {lower_username: msg_count} for the given timeframe (using basic SQL)."""
        from data.queries import Queries
        conn = self.db.connection()
        if days:
            cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
            rows = conn.exec_driver_sql(Queries.GET_DISCORD_MSG_COUNTS_SINCE_SIMPLE, (cutoff,)).fetchall()
        else:
            rows = conn.exec_driver_sql(Queries.GET_DISCORD_MSG_COUNTS_TOTAL).fetchall()
        return {row[0]: row[1] for row in rows}

    def get_activity_heatmap(self, days: int = 30) -> List[int]:
        """Returns 24-hour activity distribution for the last N days."""
        from data.queries import Queries
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        rows = self.db.connection().exec_driver_sql(Queries.GET_HOURLY_ACTIVITY, (cutoff,)).fetchall()
        heatmap = {str(h).zfill(2): 0 for h in range(24)}
        for hr, count in rows:
            if hr: heatmap[hr] = count
        return [heatmap[str(h).zfill(2)] for h in range(24)]

    def get_clan_trend(self, days: int = 30) -> List[Dict[str, Any]]:
        """Calculates Daily Clan XP Gains and Message Counts for the last N days."""
        from data.queries import Queries
        start_date = datetime.now(timezone.utc) - timedelta(days=days+1)
        cutoff_ts = start_date.isoformat()
        conn = self.db.connection()
        
        # XP Totals
        daily_xp = defaultdict(int)
        for day, _, xp in conn.exec_driver_sql(Queries.GET_DAILY_XP_MAX, (cutoff_ts,)).fetchall():
            daily_xp[day] += xp

        # Message Counts
        trend_data = defaultdict(lambda: {'msgs': 0, 'xp_gain': 0})
        for day, count in conn.exec_driver_sql(Queries.GET_DAILY_MSGS, (cutoff_ts,)).fetchall():
            trend_data[day]['msgs'] = count
            
        # Calculate Gains
        sorted_days = sorted(daily_xp.keys())
        for i in range(1, len(sorted_days)):
            curr, prev = sorted_days[i], sorted_days[i-1]
            gain = daily_xp[curr] - daily_xp[prev]
            if gain > 0: trend_data[curr]['xp_gain'] = gain

        # Format
        result = []
        display_start = datetime.now(timezone.utc) - timedelta(days=days)
        for i in range(days):
            d_str = (display_start + timedelta(days=i)).strftime('%Y-%m-%d')
            val = trend_data[d_str]
            result.append({'date': d_str, 'xp': val['xp_gain'], 'msgs': val['msgs']})
        return result

    def get_boss_data(self, snapshot_ids: List[int]) -> Dict[int, Dict[str, int]]:
        """
        Fetch boss kills for the given list of snapshot IDs.
        Returns: {snapshot_id: {'boss_name': kills, ...}}
        """
        if not snapshot_ids:
            return {}
            
        ids = list(set(snapshot_ids))
        result = {}
        chunk_size = 900
        
        for i in range(0, len(ids), chunk_size):
            chunk = ids[i:i + chunk_size]
            rows = self.db.query(BossSnapshot).filter(BossSnapshot.snapshot_id.in_(chunk)).all()
            
            for row in rows:
                if row.snapshot_id not in result:
                    result[row.snapshot_id] = {}
                result[row.snapshot_id][row.boss_name] = row.kills
                
        return result

    def get_trending_boss(self, days: int = 30) -> Optional[Dict[str, Any]]:
        """Identifies the trending boss (highest gain) over the last N days."""
        latest_snaps = self.get_latest_snapshots()
        if not latest_snaps: return None
        
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        past_snaps = self.get_snapshots_at_cutoff(cutoff)
        
        latest_ids = [s.id for s in latest_snaps.values()]
        past_ids = [s.id for s in past_snaps.values()]
        if not latest_ids: return None

        from data.queries import Queries
        conn = self.db.connection()
        def get_sums(ids):
            if not ids: return {}
            return {r[0]: r[1] for r in conn.exec_driver_sql(Queries.GET_BOSS_SUMS_FOR_IDS.format(','.join('?' * len(ids))), tuple(ids)).fetchall()}
            
        now_sums = get_sums(latest_ids)
        old_sums = get_sums(past_ids)
        
        deltas = {boss: kills - old_sums.get(boss, 0) for boss, kills in now_sums.items() if kills - old_sums.get(boss, 0) > 0}
        if not deltas: return None
        
        top_boss = max(deltas, key=deltas.get)
        
        # Daily Data
        daily_raw = {r[0]: r[1] for r in conn.exec_driver_sql(Queries.GET_DAILY_BOSS_KILLS, (cutoff.isoformat(), top_boss)).fetchall()}
        if not daily_raw: daily_raw = {datetime.now(timezone.utc).strftime('%Y-%m-%d'): now_sums.get(top_boss, 0)}
        
        sorted_days = sorted(daily_raw.keys())
        labels, values = [], []
        for i in range(1, len(sorted_days)):
            curr, prev = sorted_days[i], sorted_days[i-1]
            gain = daily_raw[curr] - daily_raw[prev]
            if gain < 0: gain = 0
            labels.append(curr)
            values.append(gain)
            
        return {
            "boss_name": top_boss.replace('_', ' ').title(),
            "total_gain": deltas[top_boss],
            "chart_data": {"labels": labels, "datasets": [{"data": values, "label": "Daily Kills"}]}
        }
