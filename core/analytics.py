"""
Analytics Service
=================
Centralized logic for calculating Clan Statistics, Time-Deltas, and Outliers.
Replaces duplicate logic in `report.py` and `dashboard_export.py`.
Uses SQLAlchemy models for strict typing and connection pooling.
"""
import logging
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session

from database.models import WOMSnapshot, DiscordMessage
from core.utils import normalize_user_string
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
                        old_map: Dict[str, WOMSnapshot]) -> Dict[str, Dict[str, int]]:
        """
        Calculates delta (XP, Boss Kills) between current and old snapshots.
        Returns: {username: {'xp': int, 'boss': int}}
        """
        gains = {}
        for user, curr in current_map.items():
            old = old_map.get(user)
            
            xp_gain = 0
            boss_gain = 0
            
            if old:
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

