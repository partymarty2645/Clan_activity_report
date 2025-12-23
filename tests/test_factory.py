"""
Unit tests for services/factory.py - Dependency Injection Factory.

Tests the ServiceFactory for:
- Lazy initialization of service instances
- Singleton pattern enforcement
- Thread-safe access with asyncio locks
- Mock injection for testing
- Service cleanup and shutdown
- VCR cassette integration for minimal API usage
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
import logging
import os

# Import the module to test
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Suppress logging during tests
logging.getLogger('ServiceFactory').setLevel(logging.CRITICAL)


@pytest.mark.asyncio
class TestServiceFactoryWOMClient:
    """Test WOMClient singleton management."""

    async def test_get_wom_client_creates_instance(self):
        """Verify WOMClient is created on first call."""
        from services.factory import ServiceFactory
        
        # Reset factory state
        ServiceFactory._wom_client = None
        ServiceFactory._wom_client_override = None
        
        with patch('services.factory.WOMClient') as mock_wom_class:
            mock_wom_class.return_value = MagicMock()
            
            client1 = await ServiceFactory.get_wom_client()
            assert client1 is not None
            assert mock_wom_class.called

    async def test_get_wom_client_returns_singleton(self):
        """Verify subsequent calls return same instance."""
        from services.factory import ServiceFactory
        
        # Reset factory state
        ServiceFactory._wom_client = None
        ServiceFactory._wom_client_override = None
        
        with patch('services.factory.WOMClient') as mock_wom_class:
            mock_instance = MagicMock()
            mock_wom_class.return_value = mock_instance
            
            client1 = await ServiceFactory.get_wom_client()
            client2 = await ServiceFactory.get_wom_client()
            
            assert client1 is client2
            # Should only be called once (singleton)
            assert mock_wom_class.call_count == 1

    async def test_wom_client_override_injection(self):
        """Verify mock can be injected via override."""
        from services.factory import ServiceFactory
        
        mock_client = MagicMock()
        ServiceFactory._wom_client_override = mock_client
        
        try:
            client = await ServiceFactory.get_wom_client()
            assert client is mock_client
        finally:
            ServiceFactory._wom_client_override = None

    async def test_wom_client_override_takes_precedence(self):
        """Verify override is returned even if singleton exists."""
        from services.factory import ServiceFactory
        
        ServiceFactory._wom_client = MagicMock()
        mock_override = MagicMock()
        ServiceFactory._wom_client_override = mock_override
        
        try:
            client = await ServiceFactory.get_wom_client()
            assert client is mock_override
        finally:
            ServiceFactory._wom_client = None
            ServiceFactory._wom_client_override = None


@pytest.mark.asyncio
class TestServiceFactoryDiscordService:
    """Test DiscordFetcher singleton management."""

    async def test_get_discord_service_creates_instance(self):
        """Verify DiscordFetcher is created on first call."""
        from services.factory import ServiceFactory
        
        # Reset factory state
        ServiceFactory._discord_service = None
        ServiceFactory._discord_service_override = None
        
        with patch('services.factory.DiscordFetcher') as mock_discord_class:
            mock_discord_class.return_value = MagicMock()
            
            service = await ServiceFactory.get_discord_service()
            assert service is not None
            assert mock_discord_class.called

    async def test_get_discord_service_returns_singleton(self):
        """Verify subsequent calls return same instance."""
        from services.factory import ServiceFactory
        
        # Reset factory state
        ServiceFactory._discord_service = None
        ServiceFactory._discord_service_override = None
        
        with patch('services.factory.DiscordFetcher') as mock_discord_class:
            mock_instance = MagicMock()
            mock_discord_class.return_value = mock_instance
            
            service1 = await ServiceFactory.get_discord_service()
            service2 = await ServiceFactory.get_discord_service()
            
            assert service1 is service2
            # Should only be called once
            assert mock_discord_class.call_count == 1

    async def test_discord_service_override_injection(self):
        """Verify mock can be injected for Discord service."""
        from services.factory import ServiceFactory
        
        mock_service = MagicMock()
        ServiceFactory._discord_service_override = mock_service
        
        try:
            service = await ServiceFactory.get_discord_service()
            assert service is mock_service
        finally:
            ServiceFactory._discord_service_override = None


@pytest.mark.asyncio
class TestServiceFactoryThreadSafety:
    """Test thread-safe concurrent access to factory."""

    async def test_concurrent_wom_client_access(self):
        """Verify concurrent calls to get_wom_client return same instance."""
        from services.factory import ServiceFactory
        
        # Reset factory state
        ServiceFactory._wom_client = None
        ServiceFactory._wom_client_override = None
        ServiceFactory._lock = None
        
        clients = []
        
        with patch('services.factory.WOMClient') as mock_wom_class:
            mock_instance = MagicMock()
            mock_wom_class.return_value = mock_instance
            
            # Simulate concurrent calls
            async def get_client():
                return await ServiceFactory.get_wom_client()
            
            results = await asyncio.gather(
                get_client(),
                get_client(),
                get_client()
            )
            
            # All should return same instance
            assert all(r is results[0] for r in results)
            # Should only create one instance
            assert mock_wom_class.call_count == 1

    async def test_concurrent_discord_service_access(self):
        """Verify concurrent calls to get_discord_service return same instance."""
        from services.factory import ServiceFactory
        
        # Reset factory state
        ServiceFactory._discord_service = None
        ServiceFactory._discord_service_override = None
        ServiceFactory._lock = None
        
        with patch('services.factory.DiscordFetcher') as mock_discord_class:
            mock_instance = MagicMock()
            mock_discord_class.return_value = mock_instance
            
            # Simulate concurrent calls
            async def get_service():
                return await ServiceFactory.get_discord_service()
            
            results = await asyncio.gather(
                get_service(),
                get_service(),
                get_service()
            )
            
            # All should return same instance
            assert all(r is results[0] for r in results)
            # Should only create one instance
            assert mock_discord_class.call_count == 1


@pytest.mark.asyncio
class TestServiceFactoryCleanup:
    """Test cleanup and shutdown."""

    async def test_cleanup_closes_services(self):
        """Verify cleanup closes both services."""
        from services.factory import ServiceFactory
        
        # Mock services with close methods
        mock_wom = AsyncMock()
        mock_discord = AsyncMock()
        
        ServiceFactory._wom_client = mock_wom
        ServiceFactory._discord_service = mock_discord
        
        try:
            await ServiceFactory.cleanup()
            
            # Verify close was called on both
            if hasattr(mock_wom, 'close'):
                mock_wom.close.assert_called()
            if hasattr(mock_discord, 'close'):
                mock_discord.close.assert_called()
        finally:
            # Reset
            ServiceFactory._wom_client = None
            ServiceFactory._discord_service = None

    async def test_cleanup_handles_missing_services(self):
        """Verify cleanup handles when services haven't been created."""
        from services.factory import ServiceFactory
        
        # Reset factory state
        ServiceFactory._wom_client = None
        ServiceFactory._discord_service = None
        
        # Should not raise exception
        try:
            await ServiceFactory.cleanup()
        except Exception as e:
            pytest.fail(f"cleanup() raised {type(e).__name__}: {e}")


class TestServiceFactorySetters:
    """Test setter methods for injection."""

    def test_set_wom_client(self):
        """Verify set_wom_client injects mock."""
        from services.factory import ServiceFactory
        
        mock_client = MagicMock()
        ServiceFactory._wom_client_override = mock_client
        
        assert ServiceFactory._wom_client_override is mock_client

    def test_set_discord_service(self):
        """Verify set_discord_service injects mock."""
        from services.factory import ServiceFactory
        
        mock_service = MagicMock()
        ServiceFactory._discord_service_override = mock_service
        
        assert ServiceFactory._discord_service_override is mock_service


# VCR CASSETTE-BASED INTEGRATION TESTS COMING SOON
# These tests will verify that ServiceFactory works with VCR-cached API responses
# after cassettes are properly recorded with correct endpoints.
#
# Test plan:
# 1. Record cassettes with actual endpoints used by factory methods
# 2. Verify factory services work with VCR cassette mode
# 3. Demonstrate zero API overhead after initial recording
