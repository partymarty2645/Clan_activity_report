"""
Dependency Injection Factory for Service Instances.

This module provides a centralized factory for creating and managing service instances
(WOMClient, DiscordFetcher, etc.). It enables:
- Lazy initialization (services created only when needed)
- Thread-safe singleton pattern
- Dependency injection for testing (can inject mocks)
- Graceful cleanup and shutdown

Usage:
    # Get real client (auto-created)
    wom = await ServiceFactory.get_wom_client()
    
    # Inject mock for testing
    ServiceFactory.set_wom_client(mock_client)
    wom = await ServiceFactory.get_wom_client()  # Returns mock
    
    # Clean up
    await ServiceFactory.cleanup()

Design:
- Static factory methods (no state)
- Thread-safe: Uses asyncio.Lock for concurrent access
- Testable: set_* methods allow easy mocking
- Decoupled: Services accessed through factory, not direct imports
"""

import asyncio
import logging
from typing import Optional
from services.wom import WOMClient
from services.discord import DiscordFetcher

logger = logging.getLogger("ServiceFactory")


class ServiceFactory:
    """
    Centralized factory for service instances.

    Manages creation, lifecycle, and injection of all service instances.
    Enables safe testing by allowing mock injection.
    """

    # Singleton instances
    _wom_client: Optional[WOMClient] = None
    _discord_service: Optional[DiscordFetcher] = None

    # Thread safety
    _lock: Optional[asyncio.Lock] = None
    _creation_lock: Optional[asyncio.Lock] = None

    # Injected instances (for testing)
    _wom_client_override: Optional[WOMClient] = None
    _discord_service_override: Optional[DiscordFetcher] = None

    @classmethod
    async def _get_lock(cls) -> asyncio.Lock:
        """Get or create the async lock for thread safety."""
        if cls._lock is None:
            cls._lock = asyncio.Lock()
        return cls._lock

    @classmethod
    async def get_wom_client(cls) -> WOMClient:
        """
        Get the WOMClient instance (singleton, lazy-initialized).

        Returns:
            WOMClient: The global WOMClient instance (or injected mock for testing)

        Notes:
            - First call creates the instance
            - Subsequent calls return the same instance
            - Thread-safe: Multiple concurrent calls don't create duplicates
            - Returns override if set via set_wom_client()
        """
        # Check override first (for testing)
        if cls._wom_client_override is not None:
            return cls._wom_client_override

        # Get lock for thread-safety
        lock = await cls._get_lock()

        # Double-check after acquiring lock (prevent race condition)
        async with lock:
            if cls._wom_client is None:
                logger.info("Initializing WOMClient...")
                cls._wom_client = WOMClient()
                logger.info("WOMClient initialized successfully")

            return cls._wom_client

    @classmethod
    async def get_discord_service(cls) -> DiscordFetcher:
        """
        Get the DiscordFetcher instance (singleton, lazy-initialized).

        Returns:
            DiscordFetcher: The global DiscordFetcher instance (or injected mock for testing)

        Notes:
            - First call creates the instance
            - Subsequent calls return the same instance
            - Thread-safe: Multiple concurrent calls don't create duplicates
            - Returns override if set via set_discord_service()
        """
        # Check override first (for testing)
        if cls._discord_service_override is not None:
            return cls._discord_service_override

        # Get lock for thread-safety
        lock = await cls._get_lock()

        # Double-check after acquiring lock (prevent race condition)
        async with lock:
            if cls._discord_service is None:
                logger.info("Initializing DiscordFetcher...")
                cls._discord_service = DiscordFetcher()
                logger.info("DiscordFetcher initialized successfully")

            return cls._discord_service

    @classmethod
    def set_wom_client(cls, client: Optional[WOMClient]) -> None:
        """
        Inject a WOMClient instance (for testing).

        Args:
            client: MockWOMClient or real WOMClient instance, or None to clear override

        Notes:
            - Used in tests to inject mocks instead of real clients
            - Example: ServiceFactory.set_wom_client(mock_wom)
            - Call with None to clear the override
        """
        cls._wom_client_override = client
        if client is not None:
            logger.info("WOMClient override set (likely testing)")

    @classmethod
    def set_discord_service(cls, service: Optional[DiscordFetcher]) -> None:
        """
        Inject a DiscordFetcher instance (for testing).

        Args:
            service: MockDiscordService or real DiscordFetcher instance, or None to clear override

        Notes:
            - Used in tests to inject mocks instead of real services
            - Example: ServiceFactory.set_discord_service(mock_discord)
            - Call with None to clear the override
        """
        cls._discord_service_override = service
        if service is not None:
            logger.info("DiscordService override set (likely testing)")

    @classmethod
    async def cleanup(cls) -> None:
        """
        Close all open connections and clean up resources.

        Should be called at program shutdown to gracefully close
        all async resources (HTTP sessions, Discord connections, etc.).

        Usage:
            try:
                # Run application
                ...
            finally:
                await ServiceFactory.cleanup()
        """
        logger.info("Cleaning up service instances...")

        # Close real WOMClient if created
        if cls._wom_client is not None:
            try:
                await cls._wom_client.close()
                logger.info("WOMClient closed")
            except Exception as e:
                logger.error(f"Error closing WOMClient: {e}")

        # Close real DiscordFetcher if created
        if cls._discord_service is not None:
            try:
                if hasattr(cls._discord_service, "close"):
                    await cls._discord_service.close()
                logger.info("DiscordFetcher closed")
            except Exception as e:
                logger.error(f"Error closing DiscordFetcher: {e}")

        logger.info("Service cleanup complete")

    @classmethod
    def reset(cls) -> None:
        """
        Reset all instances and overrides (for testing between test cases).

        This clears all cached instances and overrides, forcing fresh
        initialization on next access.

        Usage:
            @pytest.fixture
            def reset_services():
                yield
                ServiceFactory.reset()
        """
        cls._wom_client = None
        cls._discord_service = None
        cls._wom_client_override = None
        cls._discord_service_override = None
        logger.debug("ServiceFactory reset")

    @classmethod
    def get_status(cls) -> dict:
        """
        Get status of service instances.

        Returns:
            dict with keys:
            - wom_client_created: bool
            - discord_service_created: bool
            - wom_client_override: bool
            - discord_service_override: bool

        Useful for debugging and testing.
        """
        return {
            "wom_client_created": cls._wom_client is not None,
            "discord_service_created": cls._discord_service is not None,
            "wom_client_override": cls._wom_client_override is not None,
            "discord_service_override": cls._discord_service_override is not None,
        }
