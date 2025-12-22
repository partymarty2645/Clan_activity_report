"""
Unit tests for core/roles.py - Role management and authority.

Tests the ClanRole enum and RoleAuthority class for:
- Role hierarchy and tier classification
- Permission checks (leadership, officer, manage, kick)
- API name conversion
- Role grouping and retrieval
"""

import pytest
from core.roles import ClanRole, RoleAuthority


class TestClanRoleEnum:
    """Test the ClanRole enum definition and properties."""

    def test_all_roles_exist(self):
        """Verify all 10 expected roles are defined."""
        roles = list(ClanRole)
        assert len(roles) == 10
        expected_names = {
            "OWNER", "DEPUTY_OWNER", "ZENYTE", "DRAGONSTONE", "SAVIOUR",
            "ONYX", "ADMINISTRATOR", "MEMBER", "PROSPECTOR", "GUEST"
        }
        actual_names = {r.name for r in roles}
        assert actual_names == expected_names

    def test_role_api_names(self):
        """Verify each role has correct API name."""
        assert ClanRole.OWNER.api_name == "owner"
        assert ClanRole.DEPUTY_OWNER.api_name == "deputy_owner"
        assert ClanRole.ZENYTE.api_name == "zenyte"
        assert ClanRole.MEMBER.api_name == "member"
        assert ClanRole.GUEST.api_name == "guest"

    def test_role_tiers(self):
        """Verify roles have correct tier assignments."""
        tier_1 = {ClanRole.OWNER, ClanRole.DEPUTY_OWNER, ClanRole.ZENYTE, ClanRole.DRAGONSTONE, ClanRole.SAVIOUR}
        tier_2 = {ClanRole.ONYX, ClanRole.ADMINISTRATOR, ClanRole.MEMBER, ClanRole.PROSPECTOR}
        tier_3 = {ClanRole.GUEST}
        
        for role in tier_1:
            assert role.tier == 1
        for role in tier_2:
            assert role.tier == 2
        for role in tier_3:
            assert role.tier == 3

    def test_role_display_name(self):
        """Verify display_name formatting."""
        assert ClanRole.OWNER.display_name == "Owner"
        assert ClanRole.DEPUTY_OWNER.display_name == "Deputy Owner"
        assert ClanRole.ZENYTE.display_name == "Zenyte"


class TestRoleAuthorityLeadership:
    """Test leadership tier classification."""

    def test_leadership_roles(self):
        """Verify leadership role detection."""
        leadership = {
            ClanRole.OWNER, ClanRole.DEPUTY_OWNER, ClanRole.ZENYTE,
            ClanRole.DRAGONSTONE, ClanRole.SAVIOUR
        }
        for role in leadership:
            assert RoleAuthority.is_leadership(role), f"{role} should be leadership"

    def test_non_leadership_roles(self):
        """Verify non-leadership roles are not classified as leadership."""
        non_leadership = {
            ClanRole.ONYX, ClanRole.ADMINISTRATOR, ClanRole.MEMBER,
            ClanRole.PROSPECTOR, ClanRole.GUEST
        }
        for role in non_leadership:
            assert not RoleAuthority.is_leadership(role), f"{role} should not be leadership"


class TestRoleAuthorityOfficer:
    """Test officer role classification."""

    def test_officer_roles(self):
        """Verify officer role detection."""
        officers = {
            ClanRole.OWNER, ClanRole.DEPUTY_OWNER, ClanRole.ZENYTE,
            ClanRole.DRAGONSTONE, ClanRole.SAVIOUR, ClanRole.ONYX,
            ClanRole.ADMINISTRATOR
        }
        for role in officers:
            assert RoleAuthority.is_officer(role), f"{role} should be officer"

    def test_non_officer_roles(self):
        """Verify non-officer roles are not classified as officers."""
        non_officers = {ClanRole.MEMBER, ClanRole.PROSPECTOR, ClanRole.GUEST}
        for role in non_officers:
            assert not RoleAuthority.is_officer(role), f"{role} should not be officer"


class TestRoleAuthorityPermissions:
    """Test permission checks."""

    def test_can_manage_leadership_only(self):
        """Verify only leadership can manage."""
        leadership = {
            ClanRole.OWNER, ClanRole.DEPUTY_OWNER, ClanRole.ZENYTE,
            ClanRole.DRAGONSTONE, ClanRole.SAVIOUR
        }
        non_leadership = {
            ClanRole.ONYX, ClanRole.ADMINISTRATOR, ClanRole.MEMBER,
            ClanRole.PROSPECTOR, ClanRole.GUEST
        }
        
        for role in leadership:
            assert RoleAuthority.can_manage(role), f"{role} should be able to manage"
        for role in non_leadership:
            assert not RoleAuthority.can_manage(role), f"{role} should not be able to manage"

    def test_can_kick_officers_only(self):
        """Verify only officers can kick."""
        officers = {
            ClanRole.OWNER, ClanRole.DEPUTY_OWNER, ClanRole.ZENYTE,
            ClanRole.DRAGONSTONE, ClanRole.SAVIOUR, ClanRole.ONYX,
            ClanRole.ADMINISTRATOR
        }
        non_officers = {ClanRole.MEMBER, ClanRole.PROSPECTOR, ClanRole.GUEST}
        
        for role in officers:
            assert RoleAuthority.can_kick(role), f"{role} should be able to kick"
        for role in non_officers:
            assert not RoleAuthority.can_kick(role), f"{role} should not be able to kick"


class TestRoleAuthorityTier:
    """Test tier retrieval."""

    def test_get_tier(self):
        """Verify get_tier returns correct tier for each role."""
        tier_1_roles = {ClanRole.OWNER, ClanRole.DEPUTY_OWNER}
        tier_2_roles = {ClanRole.MEMBER, ClanRole.ONYX}
        tier_3_roles = {ClanRole.GUEST}
        
        for role in tier_1_roles:
            assert RoleAuthority.get_tier(role) == 1
        for role in tier_2_roles:
            assert RoleAuthority.get_tier(role) == 2
        for role in tier_3_roles:
            assert RoleAuthority.get_tier(role) == 3


class TestRoleAuthorityApiConversion:
    """Test API name to role conversion."""

    def test_from_api_name_valid(self):
        """Verify valid API names convert to correct roles."""
        assert RoleAuthority.from_api_name("owner") == ClanRole.OWNER
        assert RoleAuthority.from_api_name("deputy_owner") == ClanRole.DEPUTY_OWNER
        assert RoleAuthority.from_api_name("zenyte") == ClanRole.ZENYTE
        assert RoleAuthority.from_api_name("member") == ClanRole.MEMBER
        assert RoleAuthority.from_api_name("guest") == ClanRole.GUEST

    def test_from_api_name_case_insensitive(self):
        """Verify API conversion is case-insensitive."""
        assert RoleAuthority.from_api_name("OWNER") == ClanRole.OWNER
        assert RoleAuthority.from_api_name("Member") == ClanRole.MEMBER
        assert RoleAuthority.from_api_name("DEPUTY_OWNER") == ClanRole.DEPUTY_OWNER

    def test_from_api_name_invalid(self):
        """Verify invalid API names return None."""
        assert RoleAuthority.from_api_name("invalid_role") is None
        assert RoleAuthority.from_api_name("") is None

    def test_from_api_name_all_valid(self):
        """Verify all defined roles can be converted from API name."""
        for role in ClanRole:
            assert RoleAuthority.from_api_name(role.api_name) == role


class TestRoleAuthorityGetters:
    """Test role grouping and retrieval methods."""

    def test_get_all_roles(self):
        """Verify get_all_roles returns all 10 roles."""
        all_roles = RoleAuthority.get_all_roles()
        assert len(all_roles) == 10
        assert all(isinstance(r, ClanRole) for r in all_roles)

    def test_get_leadership_roles(self):
        """Verify get_leadership_roles returns exactly tier 1 roles."""
        leadership = RoleAuthority.get_leadership_roles()
        expected = {
            ClanRole.OWNER, ClanRole.DEPUTY_OWNER, ClanRole.ZENYTE,
            ClanRole.DRAGONSTONE, ClanRole.SAVIOUR
        }
        assert leadership == expected
        # Verify immutability (changing returned set doesn't affect internal)
        leadership.add(ClanRole.MEMBER)
        assert ClanRole.MEMBER not in RoleAuthority.get_leadership_roles()

    def test_get_officer_roles(self):
        """Verify get_officer_roles returns tier 1 + onyx + admin."""
        officers = RoleAuthority.get_officer_roles()
        expected = {
            ClanRole.OWNER, ClanRole.DEPUTY_OWNER, ClanRole.ZENYTE,
            ClanRole.DRAGONSTONE, ClanRole.SAVIOUR, ClanRole.ONYX,
            ClanRole.ADMINISTRATOR
        }
        assert officers == expected

    def test_get_tier_roles_valid(self):
        """Verify get_tier_roles returns correct roles for each tier."""
        tier_1 = RoleAuthority.get_tier_roles(1)
        expected_1 = {ClanRole.OWNER, ClanRole.DEPUTY_OWNER, ClanRole.ZENYTE, ClanRole.DRAGONSTONE, ClanRole.SAVIOUR}
        assert tier_1 == expected_1
        
        tier_2 = RoleAuthority.get_tier_roles(2)
        expected_2 = {ClanRole.ONYX, ClanRole.ADMINISTRATOR, ClanRole.MEMBER, ClanRole.PROSPECTOR}
        assert tier_2 == expected_2
        
        tier_3 = RoleAuthority.get_tier_roles(3)
        expected_3 = {ClanRole.GUEST}
        assert tier_3 == expected_3

    def test_get_tier_roles_invalid(self):
        """Verify get_tier_roles returns empty set for invalid tiers."""
        assert RoleAuthority.get_tier_roles(0) == set()
        assert RoleAuthority.get_tier_roles(4) == set()
        assert RoleAuthority.get_tier_roles(-1) == set()


class TestRoleAuthorityFormatting:
    """Test role list formatting."""

    def test_format_role_list_single(self):
        """Verify formatting a single role."""
        result = RoleAuthority.format_role_list({ClanRole.OWNER})
        assert result == "Owner"

    def test_format_role_list_multiple(self):
        """Verify formatting multiple roles."""
        roles = {ClanRole.OWNER, ClanRole.MEMBER, ClanRole.GUEST}
        result = RoleAuthority.format_role_list(roles)
        # Should be sorted by (tier, name)
        assert "Owner" in result
        assert "Member" in result
        assert "Guest" in result
        assert ", " in result

    def test_format_role_list_custom_join(self):
        """Verify custom join string."""
        roles = {ClanRole.OWNER, ClanRole.MEMBER}
        result = RoleAuthority.format_role_list(roles, join_str=" | ")
        assert " | " in result

    def test_format_role_list_empty(self):
        """Verify formatting empty set."""
        result = RoleAuthority.format_role_list(set())
        assert result == ""
