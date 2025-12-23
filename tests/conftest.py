"""
Pytest configuration and shared fixtures for ClanStats tests.

This module provides:
- Pytest fixtures for async testing
- Mock API clients that can be injected into tests
- Fixtures for database and configuration testing
- VCR cassette fixtures for recorded API responses
- Automatic cleanup after each test
"""

import pytest
import asyncio
from typing import Dict, List, Any, Optional
import sys
import os
import vcr

# Add workspace root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# VCR configuration
vcr_config = vcr.VCR(
    cassette_library_dir=os.path.join(os.path.dirname(__file__), 'cassettes'),
    record_mode='once',  # Record once, replay thereafter
    match_on=['method', 'uri'],  # Match requests by HTTP method and URI
    decode_compressed_response=True,
)


@pytest.fixture(scope="function")
def event_loop():
    """
    Create a new event loop for each test function (required for pytest-asyncio).
    
    This fixture ensures each async test gets a fresh event loop, preventing
    cross-test contamination.
    """
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


class MockWOMClient:
    """
    Mock WOM API client for testing without making real API calls.
    
    Tracks all requests made during testing and returns preset responses.
    Can be configured to fail on demand for error handling tests.
    """

    def __init__(self):
        """Initialize the mock client."""
        self.requests: List[Dict[str, Any]] = []
        self.responses: Dict[str, Any] = {}
        self.fail_on_next = False
        self._setup_default_responses()

    def _setup_default_responses(self):
        """Set up default responses for common API calls."""
        self.responses = {
            "group_members": [
                {
                    "id": 1,
                    "username": "testuser1",
                    "displayName": "TestUser1",
                    "role": "owner",
                    "joinedAt": "2023-01-01T00:00:00.000Z",
                },
                {
                    "id": 2,
                    "username": "testuser2",
                    "displayName": "TestUser2",
                    "role": "member",
                    "joinedAt": "2023-06-01T00:00:00.000Z",
                },
            ],
            "player_details": {
                "id": 1,
                "username": "testuser1",
                "displayName": "TestUser1",
                "type": "regular",
                "lastChangedAt": "2025-01-01T12:00:00.000Z",
                "lastImportedAt": "2025-01-01T12:00:00.000Z",
                "registeredAt": "2023-01-01T00:00:00.000Z",
                "updatedAt": "2025-01-01T12:00:00.000Z",
                "ehp": 4594.2,
                "ehb": 1234.5,
                "latestSnapshot": {
                    "id": 1,
                    "playerId": 1,
                    "createdAt": "2025-01-01T12:00:00.000Z",
                    "importedAt": None,
                    "data": {
                        "skills": {
                            "overall": {
                                "rank": 1000,
                                "level": 2386,
                                "experience": 4600000000,
                            }
                        },
                        "bosses": {
                            "theatre_of_blood": {"rank": 500, "kills": 250},
                            "chambers_of_xeric": {"rank": 1200, "kills": 450},
                        },
                    },
                },
            },
        }

    async def get_group_members(self, group_id: str) -> List[Dict]:
        """Mock get_group_members - returns preset member list."""
        self.requests.append({"method": "get_group_members", "group_id": group_id})

        if self.fail_on_next:
            self.fail_on_next = False
            raise Exception("Mock API error")

        return self.responses.get("group_members", [])

    async def get_player_details(self, username: str) -> Optional[Dict]:
        """Mock get_player_details - returns preset player data."""
        self.requests.append({"method": "get_player_details", "username": username})

        if self.fail_on_next:
            self.fail_on_next = False
            raise Exception("Mock API error")

        return self.responses.get("player_details")

    async def update_player(self, username: str) -> Optional[Dict]:
        """Mock update_player - simulates triggering a player update."""
        self.requests.append({"method": "update_player", "username": username})

        if self.fail_on_next:
            self.fail_on_next = False
            raise Exception("Mock API error")

        return {"message": f"Update triggered for {username}"}

    async def close(self):
        """Mock close - no-op."""
        pass


class MockDiscordService:
    """
    Mock Discord service for testing without making real API calls.
    
    Tracks all requests and returns preset Discord message data.
    Can simulate failures for error handling tests.
    """

    def __init__(self):
        """Initialize the mock service."""
        self.requests: List[Dict[str, Any]] = []
        self.responses: Dict[str, Any] = {}
        self.fail_on_next = False
        self._setup_default_responses()

    def _setup_default_responses(self):
        """Set up default responses for common Discord operations."""
        self.responses = {
            "messages": [
                {
                    "id": 123,
                    "author": "TestUser1",
                    "content": "Test message 1",
                    "created_at": "2025-01-01T10:00:00.000Z",
                },
                {
                    "id": 124,
                    "author": "TestUser2",
                    "content": "Test message 2",
                    "created_at": "2025-01-01T11:00:00.000Z",
                },
            ]
        }

    async def fetch(self, **kwargs) -> List[Dict]:
        """Mock fetch - returns preset messages."""
        self.requests.append({"method": "fetch", "kwargs": kwargs})

        if self.fail_on_next:
            self.fail_on_next = False
            raise Exception("Mock Discord error")

        return self.responses.get("messages", [])

    async def close(self):
        """Mock close - no-op."""
        pass


@pytest.fixture
def mock_wom():
    """
    Fixture providing a MockWOMClient instance.
    
    Can be used in tests to simulate WOM API calls without hitting the real API.
    """
    return MockWOMClient()


@pytest.fixture
def mock_discord():
    """
    Fixture providing a MockDiscordService instance.
    
    Can be used in tests to simulate Discord API calls without hitting the real API.
    """
    return MockDiscordService()


@pytest.fixture
def test_config():
    """
    Fixture providing test configuration.
    
    Returns a dict of test configuration values that can be used to
    override or mock Config values in tests.
    """
    return {
        "DB_FILE": ":memory:",  # In-memory SQLite for tests
        "WOM_API_KEY": "test_key",
        "DISCORD_TOKEN": "test_token",
        "WOM_GROUP_ID": "11114",
        "RELAY_CHANNEL_ID": "123456789",
    }


@pytest.fixture
def vcr_with_cassette():
    """
    Fixture providing VCR instance for cassette-based API recording/playback.
    
    Usage:
        def test_wom_api(vcr_with_cassette):
            with vcr_with_cassette.use_cassette('wom_get_group_members.yaml'):
                members = await wom_client.get_group_members('11114')
    """
    return vcr_config


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "asyncio: mark test as async (requires pytest-asyncio)"
    )
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "vcr: mark test as using VCR cassettes")


# Pytest collection
def pytest_collection_modifyitems(config, items):
    """Add asyncio marker to all async tests automatically."""
    for item in items:
        if asyncio.iscoroutinefunction(item.function):
            item.add_marker(pytest.mark.asyncio)
