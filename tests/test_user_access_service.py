"""
Test User Access Service
========================

Tests for the unified database access layer that resolves 
database access inconsistencies identified in reliability audit.

Tests cover:
- User resolution (username -> ID)
- Profile retrieval
- Statistics calculation
- Bulk operations
- Backward compatibility
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch

from services.user_access_service import UserAccessService, UserProfile, UserStats
from database.models import ClanMember, WOMSnapshot, DiscordMessage, PlayerNameAlias
from core.usernames import UsernameNormalizer


class TestUserAccessService:
    """Test unified database access service"""
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session for testing"""
        return Mock()
    
    @pytest.fixture
    def service(self, mock_db_session):
        """Create UserAccessService instance for testing"""
        return UserAccessService(mock_db_session)
    
    def test_resolve_user_id_via_alias(self, service, mock_db_session):
        """Test user resolution through PlayerNameAlias table"""
        # Mock PlayerNameAlias query result
        mock_result = Mock()
        mock_result.scalar.return_value = 123
        mock_db_session.execute.return_value = mock_result
        
        user_id = service.resolve_user_id("TestUser")
        
        assert user_id == 123
        mock_db_session.execute.assert_called_once()
    
    def test_resolve_user_id_fallback_to_clan_members(self, service, mock_db_session):
        """Test fallback to clan_members when alias not found"""
        # Mock no result from alias, but result from clan_members
        mock_alias_result = Mock()
        mock_alias_result.scalar.return_value = None
        
        mock_member_result = Mock()
        mock_member_result.scalar.return_value = 456
        
        mock_db_session.execute.side_effect = [mock_alias_result, mock_member_result]
        
        user_id = service.resolve_user_id("TestUser")
        
        assert user_id == 456
        assert mock_db_session.execute.call_count == 2
    
    def test_resolve_user_id_empty_input(self, service, mock_db_session):
        """Test handling of empty/invalid input"""
        assert service.resolve_user_id("") is None
        assert service.resolve_user_id("   ") is None
        assert service.resolve_user_id(None) is None
        
        # Should not make any database calls for invalid input
        mock_db_session.execute.assert_not_called()
    
    def test_resolve_user_id_caching(self, service, mock_db_session):
        """Test that user resolution results are cached"""
        # Mock first call
        mock_result = Mock()
        mock_result.scalar.return_value = 789
        mock_db_session.execute.return_value = mock_result
        
        # First call should hit database
        user_id1 = service.resolve_user_id("TestUser")
        assert user_id1 == 789
        
        # Second call should use cache (no additional DB call)
        user_id2 = service.resolve_user_id("TestUser")
        assert user_id2 == 789
        
        # Should only have one database call
        assert mock_db_session.execute.call_count == 1
    
    def test_get_user_profile_complete(self, service, mock_db_session):
        """Test getting complete user profile"""
        # Mock member data
        mock_member = Mock()
        mock_member.id = 123
        mock_member.username = "testuser"
        mock_member.role = "Member"
        mock_member.joined_at = datetime.now(timezone.utc)
        
        # Mock latest snapshot
        mock_snapshot = Mock()
        mock_snapshot.timestamp = datetime.now(timezone.utc)
        mock_snapshot.total_xp = 1000000
        mock_snapshot.total_boss_kills = 100
        
        # Mock results with proper method chain
        mock_member_result = Mock()
        mock_member_result.scalar_one_or_none.return_value = mock_member
        mock_member_result.scalar.return_value = mock_member
        
        mock_msg_result = Mock()
        mock_msg_result.scalar.return_value = 50
        
        mock_snapshot_result = Mock()
        mock_snapshot_result.scalar_one_or_none.return_value = mock_snapshot
        mock_snapshot_result.scalar.return_value = mock_snapshot
        
        mock_db_session.execute.side_effect = [
            mock_member_result,   # Member query
            mock_msg_result,      # Message count query  
            mock_snapshot_result  # Latest snapshot query
        ]
        
        profile = service.get_user_profile(123)
        
        assert profile is not None
        assert profile.id == 123
        assert profile.username == "testuser"
        assert profile.role == "Member"
        assert profile.discord_messages_count == 50
        assert profile.total_xp == 1000000
        assert profile.total_boss_kills == 100
    
    def test_get_user_profile_not_found(self, service, mock_db_session):
        """Test handling when user profile not found"""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_result.scalar.return_value = None
        mock_db_session.execute.return_value = mock_result
        
        profile = service.get_user_profile(999)
        
        assert profile is None
    
    def test_get_user_stats_calculation(self, service, mock_db_session):
        """Test user statistics calculation with gains"""
        # Mock member
        mock_member = Mock()
        mock_member.username = "testuser"
        
        mock_member_result = Mock()
        mock_member_result.scalar.return_value = mock_member
        
        # Mock latest snapshot (current)
        mock_latest = Mock()
        mock_latest.total_xp = 2000000
        mock_latest.total_boss_kills = 200
        
        # Mock 7-day old snapshot  
        mock_7d = Mock()
        mock_7d.total_xp = 1800000  # 200k gain in 7 days
        mock_7d.total_boss_kills = 180  # 20 kills in 7 days
        
        # Mock 30-day old snapshot
        mock_30d = Mock()
        mock_30d.total_xp = 1500000  # 500k gain in 30 days
        mock_30d.total_boss_kills = 150  # 50 kills in 30 days
        
        # Mock message counts
        mock_msgs_7d = Mock()
        mock_msgs_7d.scalar.return_value = 25
        
        mock_msgs_30d = Mock()
        mock_msgs_30d.scalar.return_value = 75
        
        # Setup execution results with both scalar methods for compatibility
        mock_latest_result = Mock()
        mock_latest_result.scalar.return_value = mock_latest
        mock_latest_result.scalar_one_or_none.return_value = mock_latest
        
        mock_7d_result = Mock()
        mock_7d_result.scalar.return_value = mock_7d
        mock_7d_result.scalar_one_or_none.return_value = mock_7d
        
        mock_30d_result = Mock()
        mock_30d_result.scalar.return_value = mock_30d
        mock_30d_result.scalar_one_or_none.return_value = mock_30d
        
        mock_db_session.execute.side_effect = [
            mock_member_result,  # Member query
            mock_latest_result,  # Latest snapshot  
            mock_7d_result,      # 7-day snapshot
            mock_30d_result,     # 30-day snapshot
            mock_msgs_7d,        # 7-day messages
            mock_msgs_30d        # 30-day messages
        ]
        
        stats = service.get_user_stats(123)
        
        assert stats is not None
        assert stats.user_id == 123
        assert stats.username == "testuser"
        assert stats.total_xp == 2000000
        assert stats.total_boss_kills == 200
        assert stats.xp_7d == 200000  # 2M - 1.8M
        assert stats.xp_30d == 500000  # 2M - 1.5M
        assert stats.boss_7d == 20     # 200 - 180
        assert stats.boss_30d == 50    # 200 - 150
        assert stats.msgs_7d == 25
        assert stats.msgs_30d == 75
    
    def test_bulk_user_resolution(self, service, mock_db_session):
        """Test bulk username resolution for performance"""
        names = ["user1", "user2", "user3", "unknown_user"]
        
        # Mock PlayerNameAlias results (user1, user2 found)
        mock_alias_results = [
            ("user1", 1),
            ("user2", 2)
        ]
        
        # Mock clan_members results (user3 found) 
        mock_member_results = [
            ("user3", 3)
        ]
        
        alias_result = Mock()
        alias_result.fetchall.return_value = mock_alias_results
        
        member_result = Mock() 
        member_result.fetchall.return_value = mock_member_results
        
        mock_db_session.execute.side_effect = [alias_result, member_result]
        
        results = service.resolve_multiple_users(names)
        
        expected = {
            "user1": 1,
            "user2": 2, 
            "user3": 3,
            "unknown_user": None
        }
        
        assert results == expected
    
    def test_legacy_format_compatibility(self, service, mock_db_session):
        """Test backward compatibility with legacy data format"""
        # Test that get_member_with_latest_stats returns expected format
        with patch.object(service, 'resolve_user_id', return_value=123), \
             patch.object(service, 'get_user_stats') as mock_get_stats, \
             patch.object(service, 'get_user_profile') as mock_get_profile:
            
            # Setup mock returns
            mock_get_stats.return_value = UserStats(
                user_id=123,
                username="testuser",
                xp_7d=100000,
                xp_30d=300000,
                boss_7d=10,
                boss_30d=25,
                msgs_7d=5,
                msgs_30d=15,
                total_xp=2000000,
                total_boss_kills=150
            )
            
            mock_get_profile.return_value = UserProfile(
                id=123,
                username="testuser",
                role="Member",
                joined_at=datetime.now(timezone.utc),
                discord_messages_count=50
            )
            
            result = service.get_member_with_latest_stats("testuser")
            
            # Verify legacy format
            assert result is not None
            assert result['username'] == "testuser"
            assert result['total_xp'] == 2000000
            assert result['total_boss'] == 150
            assert result['xp_7d'] == 100000
            assert result['xp_30d'] == 300000
            assert result['boss_7d'] == 10
            assert result['boss_30d'] == 25
            assert result['msgs_7d'] == 5
            assert result['msgs_30d'] == 15
            assert result['role'] == "Member"
    
    def test_cache_clearing(self, service, mock_db_session):
        """Test that cache can be cleared when needed"""
        # Fill cache
        mock_result = Mock()
        mock_result.scalar.return_value = 123
        mock_db_session.execute.return_value = mock_result
        
        # First call fills cache
        service.resolve_user_id("testuser")
        assert len(service._user_id_cache) == 1
        
        # Clear cache
        service.clear_cache()
        assert len(service._user_id_cache) == 0
        assert len(service._profile_cache) == 0
    
    def test_error_handling(self, service, mock_db_session):
        """Test proper error handling and logging"""
        # Mock database exception
        mock_db_session.execute.side_effect = Exception("Database error")
        
        # Should handle exceptions gracefully
        user_id = service.resolve_user_id("testuser")
        assert user_id is None
        
        profile = service.get_user_profile(123)
        assert profile is None
        
        stats = service.get_user_stats(123)
        assert stats is None


class TestUserAccessServiceIntegration:
    """Integration tests for username normalization"""
    
    def test_username_normalization_integration(self):
        """Test integration with UsernameNormalizer"""
        from core.usernames import UsernameNormalizer
        
        # Test various username formats get normalized consistently
        test_names = [
            "TestUser",
            "test user",  
            "TEST_USER",
            "test-user",
            "  test user  "
        ]
        
        # All should normalize to same value
        normalized_values = []
        for name in test_names:
            normalized = UsernameNormalizer.normalize(name, for_comparison=True)
            normalized_values.append(normalized)
            
        # All should be identical after normalization
        assert all(nv == normalized_values[0] for nv in normalized_values)
        assert normalized_values[0] == "testuser"  # Expected normalized form
    
    def test_service_initialization(self):
        """Test service can be initialized without database connection"""
        from unittest.mock import Mock
        mock_db = Mock()
        service = UserAccessService(mock_db)
        
        # Should initialize without errors
        assert service is not None
        assert hasattr(service, 'db')
        assert hasattr(service, 'clear_cache')
        assert hasattr(service, 'resolve_user_id')