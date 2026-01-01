"""
User Access Service - Unified Database Access Layer
=====================================================

Resolves the critical database access inconsistency problem identified in reliability audit.

PROBLEM SOLVED:
- Mixed ID vs username queries across codebase
- author_name vs username confusion between Discord and database
- Inconsistent fuzzy matching vs exact matching
- Multiple identity resolution systems (identity_map.json, PlayerNameAlias, direct lookups)

UNIFIED ACCESS PATTERNS:
✅ Single point of truth for user resolution
✅ Consistent username normalization
✅ Fallback hierarchy for identity matching
✅ Type-safe database queries
✅ Performance-optimized with caching

Usage:
    service = UserAccessService(db_session)
    user_id = service.resolve_user_id("username") 
    user_data = service.get_user_profile(user_id)
    member_stats = service.get_member_with_latest_stats("username")
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple, cast
from dataclasses import dataclass
from functools import lru_cache

from sqlalchemy import select, func, and_, or_, text, desc
from sqlalchemy.orm import Session

from database.models import ClanMember, WOMSnapshot, DiscordMessage, PlayerNameAlias, BossSnapshot
from core.usernames import UsernameNormalizer
from core.config import Config

logger = logging.getLogger("UserAccessService")

@dataclass
class UserProfile:
    """Unified user profile structure"""
    id: int
    username: str
    role: Optional[str]
    joined_at: Optional[datetime]
    discord_messages_count: int = 0
    latest_snapshot_date: Optional[datetime] = None
    total_xp: Optional[int] = None
    total_boss_kills: Optional[int] = None

@dataclass
class UserStats:
    """User statistics for analytics"""
    user_id: int
    username: str
    xp_7d: int = 0
    xp_30d: int = 0
    boss_7d: int = 0
    boss_30d: int = 0
    msgs_7d: int = 0
    msgs_30d: int = 0
    total_xp: int = 0
    total_boss_kills: int = 0

class UserAccessService:
    """
    Unified Database Access Service
    
    Provides consistent, type-safe access to user data across all systems.
    Replaces inconsistent database access patterns identified in reliability audit.
    """
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self._user_id_cache: Dict[str, Optional[int]] = {}
        self._profile_cache: Dict[int, UserProfile] = {}
        
    def clear_cache(self) -> None:
        """Clear internal caches - call after database updates"""
        self._user_id_cache.clear()
        self._profile_cache.clear()
        
    # ========================================
    # CORE USER RESOLUTION (Primary Interface)
    # ========================================
    
    def resolve_user_id(self, name: str, use_cache: bool = True) -> Optional[int]:
        """
        Resolve ANY name variation to canonical user ID.
        
        Resolution hierarchy:
        1. PlayerNameAlias table (handles username changes)
        2. Direct clan_members lookup (normalized username)
        3. Discord author_name fuzzy matching (fallback)
        
        Args:
            name: Any username variation (Discord author_name, WOM username, etc.)
            use_cache: Whether to use internal cache for performance
            
        Returns:
            ClanMember.id if found, None otherwise
        """
        if not name or not name.strip():
            return None
            
        normalized = UsernameNormalizer.normalize(name, for_comparison=True)
        if not normalized:
            return None
            
        # Check cache first
        if use_cache and normalized in self._user_id_cache:
            return self._user_id_cache[normalized]
            
        user_id = None
        
        try:
            # 1. Check PlayerNameAlias table (most accurate)
            alias_stmt = select(PlayerNameAlias.member_id).where(
                PlayerNameAlias.normalized_name == normalized
            ).limit(1)
            alias_result = self.db.execute(alias_stmt).scalar()
            
            if alias_result:
                user_id = alias_result
                logger.debug(f"Resolved '{name}' via PlayerNameAlias -> ID {user_id}")
            else:
                # 2. Direct clan_members lookup
                member_stmt = select(ClanMember.id).where(
                    ClanMember.username == normalized
                ).limit(1)
                member_result = self.db.execute(member_stmt).scalar()
                
                if member_result:
                    user_id = member_result
                    logger.debug(f"Resolved '{name}' via direct ClanMember -> ID {user_id}")
                else:
                    # 3. Fuzzy Discord author_name matching (last resort)
                    discord_stmt = select(DiscordMessage.user_id).where(
                        and_(
                            DiscordMessage.author_name.ilike(f"%{normalized}%"),
                            DiscordMessage.user_id.isnot(None)
                        )
                    ).limit(1)
                    discord_result = self.db.execute(discord_stmt).scalar()
                    
                    if discord_result:
                        user_id = discord_result
                        logger.debug(f"Resolved '{name}' via Discord fuzzy match -> ID {user_id}")
                        
        except Exception as e:
            logger.error(f"Error resolving user_id for '{name}': {e}")
            user_id = None
            
        # Cache result (including None)
        if use_cache:
            self._user_id_cache[normalized] = user_id
            
        return user_id
    
    def get_user_profile(self, user_id: int, use_cache: bool = True) -> Optional[UserProfile]:
        """
        Get complete user profile by ID.
        
        Combines data from clan_members, discord_messages, and wom_snapshots
        into unified UserProfile structure.
        """
        if use_cache and user_id in self._profile_cache:
            return self._profile_cache[user_id]
            
        try:
            # Get base member data
            member_stmt = select(ClanMember).where(ClanMember.id == user_id)
            member_result = self.db.execute(member_stmt)
            member = cast(Optional[ClanMember], member_result.scalar_one_or_none() if hasattr(member_result, 'scalar_one_or_none') else member_result.scalar())
            
            if not member:
                return None
                
            # Get Discord message count
            msg_count_stmt = select(func.count(DiscordMessage.id)).where(
                DiscordMessage.user_id == user_id
            )
            msg_count = self.db.execute(msg_count_stmt).scalar() or 0
            
            # Get latest snapshot data
            latest_snapshot_stmt = select(WOMSnapshot).where(
                WOMSnapshot.user_id == user_id
            ).order_by(desc(WOMSnapshot.timestamp)).limit(1)
            snapshot_result = self.db.execute(latest_snapshot_stmt)
            latest_snapshot = cast(Optional[WOMSnapshot], snapshot_result.scalar_one_or_none() if hasattr(snapshot_result, 'scalar_one_or_none') else snapshot_result.scalar())
            
            profile = UserProfile(
                id=cast(int, member.id),
                username=cast(str, member.username),
                role=cast(Optional[str], member.role),
                joined_at=cast(Optional[datetime], member.joined_at),
                discord_messages_count=msg_count,
                latest_snapshot_date=cast(Optional[datetime], latest_snapshot.timestamp) if latest_snapshot else None,
                total_xp=cast(Optional[int], latest_snapshot.total_xp) if latest_snapshot else None,
                total_boss_kills=cast(Optional[int], latest_snapshot.total_boss_kills) if latest_snapshot else None
            )
            
            if use_cache:
                self._profile_cache[user_id] = profile
                
            return profile
            
        except Exception as e:
            logger.error(f"Error getting user profile for ID {user_id}: {e}")
            return None
    
    def get_user_stats(self, user_id: int, days_back: int = 30) -> Optional[UserStats]:
        """
        Get comprehensive user statistics for analytics.
        
        Replaces inconsistent stat gathering across multiple scripts.
        Calculates XP/boss gains and message counts over specified period.
        """
        try:
            # Get base member data
            member_stmt = select(ClanMember).where(ClanMember.id == user_id)
            member_result = self.db.execute(member_stmt)
            member = member_result.scalar()
            
            if not member:
                return None
                
            # Calculate cutoff dates
            now = datetime.now(timezone.utc)
            cutoff_7d = now - timedelta(days=7)
            cutoff_30d = now - timedelta(days=30)
            cutoff_custom = now - timedelta(days=days_back)
            
            # Get latest and historical snapshots
            latest_stmt = select(WOMSnapshot).where(
                WOMSnapshot.user_id == user_id
            ).order_by(desc(WOMSnapshot.timestamp)).limit(1)
            latest_result = self.db.execute(latest_stmt)
            latest = latest_result.scalar_one_or_none() if hasattr(latest_result, 'scalar_one_or_none') else latest_result.scalar()
            
            snapshot_7d_stmt = select(WOMSnapshot).where(
                and_(
                    WOMSnapshot.user_id == user_id,
                    WOMSnapshot.timestamp <= cutoff_7d
                )
            ).order_by(desc(WOMSnapshot.timestamp)).limit(1)
            snapshot_7d_result = self.db.execute(snapshot_7d_stmt)
            snapshot_7d = snapshot_7d_result.scalar_one_or_none() if hasattr(snapshot_7d_result, 'scalar_one_or_none') else snapshot_7d_result.scalar()
            
            snapshot_30d_stmt = select(WOMSnapshot).where(
                and_(
                    WOMSnapshot.user_id == user_id,
                    WOMSnapshot.timestamp <= cutoff_30d
                )
            ).order_by(desc(WOMSnapshot.timestamp)).limit(1)
            snapshot_30d_result = self.db.execute(snapshot_30d_stmt)
            snapshot_30d = snapshot_30d_result.scalar_one_or_none() if hasattr(snapshot_30d_result, 'scalar_one_or_none') else snapshot_30d_result.scalar()
            
            # Calculate gains
            latest_total_xp = cast(Optional[int], latest.total_xp) if latest else None
            latest_total_boss_kills = cast(Optional[int], latest.total_boss_kills) if latest else None

            total_xp = int(latest_total_xp) if latest_total_xp is not None else 0
            total_boss_kills = int(latest_total_boss_kills) if latest_total_boss_kills is not None else 0
            
            snapshot_7d_xp_raw = cast(Optional[int], snapshot_7d.total_xp) if snapshot_7d else None
            snapshot_30d_xp_raw = cast(Optional[int], snapshot_30d.total_xp) if snapshot_30d else None
            
            snapshot_7d_boss_raw = cast(Optional[int], snapshot_7d.total_boss_kills) if snapshot_7d else None
            snapshot_30d_boss_raw = cast(Optional[int], snapshot_30d.total_boss_kills) if snapshot_30d else None
            
            snapshot_7d_xp = int(snapshot_7d_xp_raw) if snapshot_7d_xp_raw is not None else total_xp
            snapshot_30d_xp = int(snapshot_30d_xp_raw) if snapshot_30d_xp_raw is not None else total_xp
            
            snapshot_7d_boss = int(snapshot_7d_boss_raw) if snapshot_7d_boss_raw is not None else total_boss_kills
            snapshot_30d_boss = int(snapshot_30d_boss_raw) if snapshot_30d_boss_raw is not None else total_boss_kills
            
            xp_7d = total_xp - snapshot_7d_xp
            xp_30d = total_xp - snapshot_30d_xp
            
            boss_7d = total_boss_kills - snapshot_7d_boss
            boss_30d = total_boss_kills - snapshot_30d_boss
            
            # Get message counts
            msgs_7d_stmt = select(func.count(DiscordMessage.id)).where(
                and_(
                    DiscordMessage.user_id == user_id,
                    DiscordMessage.created_at >= cutoff_7d
                )
            )
            msgs_7d = self.db.execute(msgs_7d_stmt).scalar() or 0
            
            msgs_30d_stmt = select(func.count(DiscordMessage.id)).where(
                and_(
                    DiscordMessage.user_id == user_id,
                    DiscordMessage.created_at >= cutoff_30d
                )
            )
            msgs_30d = self.db.execute(msgs_30d_stmt).scalar() or 0
            
            return UserStats(
                user_id=user_id,
                username=cast(str, member.username),
                xp_7d=max(0, xp_7d),  # Prevent negative gains
                xp_30d=max(0, xp_30d),
                boss_7d=max(0, boss_7d),
                boss_30d=max(0, boss_30d),
                msgs_7d=msgs_7d,
                msgs_30d=msgs_30d,
                total_xp=total_xp,
                total_boss_kills=total_boss_kills
            )
            
        except Exception as e:
            logger.error(f"Error getting user stats for ID {user_id}: {e}")
            return None
    
    # ========================================
    # BULK OPERATIONS (Performance Optimized)
    # ========================================
    
    def get_all_active_members(self, days_back: int = 30) -> List[UserStats]:
        """
        Get statistics for all active members in a single optimized query.
        
        Replaces inefficient individual user lookups in analytics scripts.
        """
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
            
            # Complex query that joins all necessary data in one go
            query = text("""
                WITH latest_snapshots AS (
                    SELECT 
                        user_id,
                        total_xp,
                        total_boss_kills,
                        timestamp,
                        ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY timestamp DESC) as rn
                    FROM wom_snapshots 
                    WHERE user_id IS NOT NULL
                ),
                snapshot_7d AS (
                    SELECT 
                        user_id,
                        total_xp as xp_7d_ago,
                        total_boss_kills as boss_7d_ago,
                        ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY timestamp DESC) as rn
                    FROM wom_snapshots 
                    WHERE user_id IS NOT NULL 
                    AND timestamp <= datetime('now', '-7 days')
                ),
                snapshot_30d AS (
                    SELECT 
                        user_id,
                        total_xp as xp_30d_ago,
                        total_boss_kills as boss_30d_ago,
                        ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY timestamp DESC) as rn
                    FROM wom_snapshots 
                    WHERE user_id IS NOT NULL 
                    AND timestamp <= datetime('now', '-30 days')
                )
                SELECT 
                    cm.id,
                    cm.username,
                    COALESCE(ls.total_xp, 0) as total_xp,
                    COALESCE(ls.total_boss_kills, 0) as total_boss_kills,
                    COALESCE(ls.total_xp - s7.xp_7d_ago, 0) as xp_7d,
                    COALESCE(ls.total_xp - s30.xp_30d_ago, 0) as xp_30d,
                    COALESCE(ls.total_boss_kills - s7.boss_7d_ago, 0) as boss_7d,
                    COALESCE(ls.total_boss_kills - s30.boss_30d_ago, 0) as boss_30d,
                    (SELECT COUNT(*) FROM discord_messages dm 
                     WHERE dm.user_id = cm.id 
                     AND dm.created_at >= datetime('now', '-7 days')) as msgs_7d,
                    (SELECT COUNT(*) FROM discord_messages dm 
                     WHERE dm.user_id = cm.id 
                     AND dm.created_at >= datetime('now', '-30 days')) as msgs_30d
                FROM clan_members cm
                LEFT JOIN latest_snapshots ls ON cm.id = ls.user_id AND ls.rn = 1
                LEFT JOIN snapshot_7d s7 ON cm.id = s7.user_id AND s7.rn = 1
                LEFT JOIN snapshot_30d s30 ON cm.id = s30.user_id AND s30.rn = 1
                ORDER BY total_xp DESC
            """)
            
            results = self.db.execute(query).fetchall()
            
            stats_list = []
            for row in results:
                stats_list.append(UserStats(
                    user_id=row[0],
                    username=row[1],
                    total_xp=row[2],
                    total_boss_kills=row[3],
                    xp_7d=max(0, row[4] or 0),
                    xp_30d=max(0, row[5] or 0),
                    boss_7d=max(0, row[6] or 0),
                    boss_30d=max(0, row[7] or 0),
                    msgs_7d=row[8] or 0,
                    msgs_30d=row[9] or 0
                ))
                
            logger.info(f"Retrieved stats for {len(stats_list)} active members")
            return stats_list
            
        except Exception as e:
            logger.error(f"Error getting bulk member stats: {e}")
            return []
    
    def resolve_multiple_users(self, names: List[str]) -> Dict[str, Optional[int]]:
        """
        Resolve multiple usernames to IDs in a single optimized operation.
        
        Returns dict mapping input names to resolved user IDs (or None if not found).
        """
        results = {}
        normalized_names = []
        name_mapping = {}
        
        # Normalize all names and create mapping
        for name in names:
            if name and name.strip():
                normalized = UsernameNormalizer.normalize(name, for_comparison=True)
                if normalized:
                    normalized_names.append(normalized)
                    name_mapping[normalized] = name
                    
        if not normalized_names:
            return {name: None for name in names}
            
        try:
            # Bulk query PlayerNameAlias
            alias_stmt = select(
                PlayerNameAlias.normalized_name, 
                PlayerNameAlias.member_id
            ).where(PlayerNameAlias.normalized_name.in_(normalized_names))
            alias_results = self.db.execute(alias_stmt).fetchall()
            
            found_via_alias = {}
            for norm_name, member_id in alias_results:
                original_name = name_mapping[norm_name]
                found_via_alias[norm_name] = member_id
                results[original_name] = member_id
                
            # Find remaining names not found via alias
            remaining_names = [n for n in normalized_names if n not in found_via_alias]
            
            if remaining_names:
                # Bulk query clan_members for remaining
                member_stmt = select(
                    ClanMember.username, 
                    ClanMember.id
                ).where(ClanMember.username.in_(remaining_names))
                member_results = self.db.execute(member_stmt).fetchall()
                
                for username, member_id in member_results:
                    original_name = name_mapping[username]
                    results[original_name] = member_id
                    
            # Fill in None for any names not found
            for name in names:
                if name not in results:
                    results[name] = None
                    
            return results
            
        except Exception as e:
            logger.error(f"Error in bulk user resolution: {e}")
            return {name: None for name in names}
    
    # ========================================
    # COMPATIBILITY METHODS (Migration Support)
    # ========================================
    
    def get_member_with_latest_stats(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Backward compatibility method for existing code.
        
        Returns data in format expected by current analytics scripts.
        """
        user_id = self.resolve_user_id(username)
        if not user_id:
            return None
            
        stats = self.get_user_stats(user_id)
        if not stats:
            return None
            
        profile = self.get_user_profile(user_id)
        if not profile:
            return None
            
        # Return in legacy format for compatibility
        return {
            'username': stats.username,
            'total_xp': stats.total_xp,
            'total_boss': stats.total_boss_kills,
            'xp_7d': stats.xp_7d,
            'xp_30d': stats.xp_30d,
            'boss_7d': stats.boss_7d,
            'boss_30d': stats.boss_30d,
            'msgs_7d': stats.msgs_7d,
            'msgs_30d': stats.msgs_30d,
            'role': profile.role,
            'joined_at': profile.joined_at
        }
    
    def get_all_members_legacy_format(self) -> List[Dict[str, Any]]:
        """
        Get all members in legacy format for backward compatibility.
        
        Gradually migrate calling code to use get_all_active_members() instead.
        """
        active_stats = self.get_all_active_members()
        
        legacy_format = []
        for stats in active_stats:
            profile = self.get_user_profile(stats.user_id)
            legacy_format.append({
                'username': stats.username,
                'total_xp': stats.total_xp,
                'total_boss': stats.total_boss_kills,
                'xp_7d': stats.xp_7d,
                'xp_30d': stats.xp_30d,
                'boss_7d': stats.boss_7d,
                'boss_30d': stats.boss_30d,
                'msgs_7d': stats.msgs_7d,
                'msgs_30d': stats.msgs_30d,
                'role': profile.role if profile else None,
                'joined_at': profile.joined_at if profile else None
            })
            
        return legacy_format