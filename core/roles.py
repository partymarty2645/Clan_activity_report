"""
Role Management - Centralized clan role definitions and authority.

This module provides a single source of truth for all clan role information,
permissions, and hierarchy. All code accessing roles should use the ClanRole
enum and RoleAuthority class rather than hardcoding role lists.

Role Hierarchy (by tier):
- Tier 1 (Leadership): Owner, Deputy Owner, Zenyte, Dragonstone, Saviour
- Tier 2 (Officers): Onyx, Administrator, Member, Prospector
- Tier 3 (Guest): Guest

Design Principles:
- Single source of truth for all roles
- Roles are immutable (Enum)
- Permissions centralized (RoleAuthority)
- Easy to extend with new roles without changing calling code
"""

from enum import Enum
from typing import Set, Dict, Optional
import logging

logger = logging.getLogger("RoleAuthority")


class ClanRole(Enum):
    """
    Enumeration of all valid clan roles.
    
    Each role is defined with its tier (1=leadership, 2=staff, 3=regular) and
    API name (as returned by WOM API).
    """

    OWNER = ("owner", 1)
    DEPUTY_OWNER = ("deputy_owner", 1)
    ZENYTE = ("zenyte", 1)
    DRAGONSTONE = ("dragonstone", 1)
    SAVIOUR = ("saviour", 1)
    ONYX = ("onyx", 2)
    ADMINISTRATOR = ("administrator", 2)
    MEMBER = ("member", 2)
    PROSPECTOR = ("prospector", 2)
    GUEST = ("guest", 3)

    def __init__(self, api_name: str, tier: int):
        self.api_name = api_name
        self.tier = tier

    @property
    def display_name(self) -> str:
        """Return human-readable role name."""
        return self.name.replace("_", " ").title()


class RoleAuthority:
    """
    Centralized role authority and permissions management.

    This class provides static methods for role-based queries and operations.
    Use these methods instead of hardcoding role lists anywhere in the codebase.
    """

    # Role hierarchies and groupings
    _TIER_1_ROLES: Set[ClanRole] = {
        ClanRole.OWNER,
        ClanRole.DEPUTY_OWNER,
        ClanRole.ZENYTE,
        ClanRole.DRAGONSTONE,
        ClanRole.SAVIOUR,
    }

    _TIER_2_ROLES: Set[ClanRole] = {
        ClanRole.ONYX,
        ClanRole.ADMINISTRATOR,
        ClanRole.MEMBER,
        ClanRole.PROSPECTOR,
    }

    _TIER_3_ROLES: Set[ClanRole] = {ClanRole.GUEST}

    _OFFICER_ROLES: Set[ClanRole] = _TIER_1_ROLES | {ClanRole.ONYX, ClanRole.ADMINISTRATOR}

    # Cache for API name to role mapping
    _API_NAME_MAP: Optional[Dict[str, ClanRole]] = None

    @classmethod
    def _build_api_map(cls) -> Dict[str, ClanRole]:
        """Build and cache the API name to role mapping."""
        if cls._API_NAME_MAP is None:
            cls._API_NAME_MAP = {role.api_name: role for role in ClanRole}
        return cls._API_NAME_MAP

    @staticmethod
    def is_leadership(role: ClanRole) -> bool:
        """
        Check if a role is in the leadership tier (Tier 1).

        Leadership roles include: Owner, Deputy Owner, Zenyte, Dragonstone, Saviour

        Args:
            role: The ClanRole to check

        Returns:
            True if the role is a leadership role, False otherwise

        Examples:
            >>> RoleAuthority.is_leadership(ClanRole.OWNER)
            True
            >>> RoleAuthority.is_leadership(ClanRole.MEMBER)
            False
        """
        return role in RoleAuthority._TIER_1_ROLES

    @staticmethod
    def is_officer(role: ClanRole) -> bool:
        """
        Check if a role is an officer role (leadership + Onyx + Administrator).

        Officer roles include: Tier 1 + Onyx + Administrator

        Args:
            role: The ClanRole to check

        Returns:
            True if the role is an officer role, False otherwise

        Examples:
            >>> RoleAuthority.is_officer(ClanRole.ZENYTE)
            True
            >>> RoleAuthority.is_officer(ClanRole.ONYX)
            True
            >>> RoleAuthority.is_officer(ClanRole.MEMBER)
            False
        """
        return role in RoleAuthority._OFFICER_ROLES

    @staticmethod
    def can_manage(role: ClanRole) -> bool:
        """
        Check if a role can manage other members (leadership only).

        Args:
            role: The ClanRole to check

        Returns:
            True if the role has management permissions, False otherwise
        """
        return RoleAuthority.is_leadership(role)

    @staticmethod
    def can_kick(role: ClanRole) -> bool:
        """
        Check if a role can kick members (officers and above).

        Args:
            role: The ClanRole to check

        Returns:
            True if the role can perform kicks, False otherwise
        """
        return RoleAuthority.is_officer(role)

    @staticmethod
    def get_tier(role: ClanRole) -> int:
        """
        Get the tier level of a role.

        Args:
            role: The ClanRole to check

        Returns:
            Tier level (1=leadership, 2=officer, 3=regular member/guest)
        """
        return role.tier

    @staticmethod
    def from_api_name(api_name: str) -> Optional[ClanRole]:
        """
        Convert an API role name string to a ClanRole enum.

        This is the safe way to convert WOM API role strings to our internal representation.

        Args:
            api_name: The role name from the WOM API (e.g., 'owner', 'member')

        Returns:
            The corresponding ClanRole, or None if the API name is not recognized

        Examples:
            >>> RoleAuthority.from_api_name('owner')
            <ClanRole.OWNER: ('owner', 1)>

            >>> RoleAuthority.from_api_name('invalid_role') is None
            True
        """
        if not api_name:
            return None

        api_map = RoleAuthority._build_api_map()
        role = api_map.get(api_name.lower())

        if role is None:
            logger.warning(f"Unknown API role name: {api_name}")

        return role

    @staticmethod
    def get_all_roles() -> Set[ClanRole]:
        """
        Get all defined roles.

        Returns:
            Set of all ClanRole values
        """
        return set(ClanRole)

    @staticmethod
    def get_leadership_roles() -> Set[ClanRole]:
        """Get all leadership (Tier 1) roles."""
        return RoleAuthority._TIER_1_ROLES.copy()

    @staticmethod
    def get_officer_roles() -> Set[ClanRole]:
        """Get all officer roles (Tier 1 + Onyx + Administrator)."""
        return RoleAuthority._OFFICER_ROLES.copy()

    @staticmethod
    def get_tier_roles(tier: int) -> Set[ClanRole]:
        """
        Get all roles in a specific tier.

        Args:
            tier: The tier level (1, 2, or 3)

        Returns:
            Set of roles in that tier, or empty set if tier is invalid
        """
        if tier == 1:
            return RoleAuthority._TIER_1_ROLES.copy()
        elif tier == 2:
            return RoleAuthority._TIER_2_ROLES.copy()
        elif tier == 3:
            return RoleAuthority._TIER_3_ROLES.copy()
        else:
            logger.warning(f"Invalid tier: {tier}")
            return set()

    @staticmethod
    def format_role_list(roles: Set[ClanRole], join_str: str = ", ") -> str:
        """
        Format a set of roles as a human-readable string.

        Args:
            roles: Set of ClanRole values
            join_str: String to join role names with (default: ", ")

        Returns:
            Human-readable role list (e.g., "Owner, Deputy Owner, Zenyte")
        """
        return join_str.join(role.display_name for role in sorted(roles, key=lambda r: (r.tier, r.name)))
