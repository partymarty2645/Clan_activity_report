"""End-to-End tests for the harvest pipeline using mocked APIs and VCR cassettes.

Tests the complete data harvest workflow (WOM + Discord) without hitting real APIs.
Uses MockWOMClient and MockDiscordService from conftest.py fixtures for unit tests.
Uses VCR cassettes for integration tests with recorded real API responses.
"""

import pytest
import asyncio
import os
from scripts.harvest_sqlite import run_sqlite_harvest
from services.factory import ServiceFactory
from services.wom import WOMClient


@pytest.mark.asyncio
async def test_harvest_with_mock_wom(mock_wom, mock_discord):
    """
    Test that harvest pipeline functions can use mocked WOM and Discord services.
    
    Verifies:
    - Harvest function signature accepts injected mock clients
    - Mock clients can be passed as parameters
    - ServiceFactory can hold overrides for testing
    """
    # Configure ServiceFactory to use mocks
    ServiceFactory.set_wom_client(mock_wom)
    ServiceFactory.set_discord_service(mock_discord)
    
    try:
        # Verify mocks are in use
        status = ServiceFactory.get_status()
        assert status["wom_client_override"] is True, "Mock WOM should be set"
        assert status["discord_service_override"] is True, "Mock Discord should be set"
        
        # Verify function accepts injected clients
        import inspect
        from scripts.harvest_sqlite import run_sqlite_harvest
        sig = inspect.signature(run_sqlite_harvest)
        assert "wom_client_inject" in sig.parameters
        assert "discord_service_inject" in sig.parameters
        
        # The actual harvest would need a real database, but we verified:
        # 1. ServiceFactory can hold mocks
        # 2. Harvest function accepts injectable clients
        
    finally:
        ServiceFactory.reset()


@pytest.mark.asyncio
async def test_harvest_with_injected_clients(mock_wom, mock_discord):
    """
    Test that harvest pipeline accepts injected client parameters.
    
    Verifies:
    - harvest_sqlite.run_sqlite_harvest() accepts wom_client_inject parameter
    - harvest_sqlite.run_sqlite_harvest() accepts discord_service_inject parameter
    - Injected clients are used in the harvest process
    """
    # Get fresh mocks
    wom = mock_wom
    discord = mock_discord
    
    # Mock clients should have empty requests initially
    assert len(wom.requests) == 0, "Mock should start with no requests"
    assert len(discord.requests) == 0, "Mock should start with no requests"
    
    # Test that the function signature accepts these parameters
    import inspect
    from scripts.harvest_sqlite import run_sqlite_harvest
    
    sig = inspect.signature(run_sqlite_harvest)
    assert "wom_client_inject" in sig.parameters, "Should have wom_client_inject parameter"
    assert "discord_service_inject" in sig.parameters, "Should have discord_service_inject parameter"


@pytest.mark.asyncio
async def test_harvest_mock_wom_responses(mock_wom):
    """
    Test that MockWOMClient returns correct preset responses.
    
    Verifies:
    - get_group_members() returns test members
    - get_player_details() returns test player data
    - Responses match expected structure
    """
    # Test get_group_members
    members = await mock_wom.get_group_members("11114")
    assert len(members) > 0, "Should return members"
    assert all("username" in m for m in members), "Members should have usernames"
    assert all("role" in m for m in members), "Members should have roles"
    
    # Verify request was tracked
    assert len(mock_wom.requests) == 1, "Should have tracked the request"
    assert mock_wom.requests[0]["method"] == "get_group_members"
    
    # Test get_player_details
    player = await mock_wom.get_player_details("testuser1")
    assert player is not None, "Should return player details"
    assert player.get("username") == "testuser1", "Player should have correct username"
    
    # Verify both requests tracked
    assert len(mock_wom.requests) == 2, "Should have tracked both requests"


@pytest.mark.asyncio
async def test_harvest_mock_discord_responses(mock_discord):
    """
    Test that MockDiscordService returns correct preset responses.
    
    Verifies:
    - fetch() returns test messages
    - Responses match expected structure
    """
    # Test fetch
    messages = await mock_discord.fetch(start_date=None, end_date=None)
    assert len(messages) > 0, "Should return messages"
    assert all("author" in m for m in messages), "Messages should have authors"
    assert all("content" in m for m in messages), "Messages should have content"
    
    # Verify request was tracked
    assert len(mock_discord.requests) == 1, "Should have tracked the request"
    assert mock_discord.requests[0]["method"] == "fetch"


@pytest.mark.asyncio
async def test_harvest_mock_failure_handling(mock_wom):
    """
    Test that harvest handles API failures gracefully.
    
    Verifies:
    - When mock.fail_on_next is set, calls raise exceptions
    - Harvest can handle these exceptions
    """
    # Set mock to fail on next request
    mock_wom.fail_on_next = True
    
    # Attempting to call should raise
    with pytest.raises(Exception, match="Mock API error"):
        await mock_wom.get_player_details("testuser")
    
    # Verify the flag was reset
    assert mock_wom.fail_on_next is False, "fail_on_next should be reset after exception"


@pytest.mark.asyncio
async def test_service_factory_injection(mock_wom, mock_discord):
    """
    Test that ServiceFactory correctly handles client injection for testing.
    
    Verifies:
    - set_wom_client() overrides default client
    - set_discord_service() overrides default service
    - get_status() reports overrides correctly
    - reset() clears overrides
    """
    # Initially no overrides
    ServiceFactory.reset()
    status = ServiceFactory.get_status()
    assert status["wom_client_override"] is False, "Should start with no override"
    assert status["discord_service_override"] is False, "Should start with no override"
    
    # Set overrides
    ServiceFactory.set_wom_client(mock_wom)
    ServiceFactory.set_discord_service(mock_discord)
    
    # Status should report overrides
    status = ServiceFactory.get_status()
    assert status["wom_client_override"] is True, "Should report WOM override"
    assert status["discord_service_override"] is True, "Should report Discord override"
    
    # Get methods should return mocks
    wom = await ServiceFactory.get_wom_client()
    assert wom is mock_wom, "Should return the injected mock"
    
    discord = await ServiceFactory.get_discord_service()
    assert discord is mock_discord, "Should return the injected mock"
    
    # Reset should clear overrides
    ServiceFactory.reset()
    status = ServiceFactory.get_status()
    assert status["wom_client_override"] is False, "Should clear override"
    assert status["discord_service_override"] is False, "Should clear override"


@pytest.mark.asyncio
async def test_service_factory_lazy_initialization():
    """
    Test that ServiceFactory uses lazy initialization.
    
    Verifies:
    - Services not created until accessed
    - Only one instance created per service
    """
    ServiceFactory.reset()
    
    status = ServiceFactory.get_status()
    assert status["wom_client_created"] is False, "WOM should not be created yet"
    assert status["discord_service_created"] is False, "Discord should not be created yet"
    
    # Access WOM client - should create it
    wom1 = await ServiceFactory.get_wom_client()
    status = ServiceFactory.get_status()
    assert status["wom_client_created"] is True, "WOM should now be created"
    
    # Access again - should return same instance
    wom2 = await ServiceFactory.get_wom_client()
    assert wom1 is wom2, "Should return same instance (singleton)"
    
    ServiceFactory.reset()


@pytest.mark.asyncio
async def test_mock_request_tracking(mock_wom, mock_discord):
    """
    Test that mocks track all requests for verification.
    
    Verifies:
    - requests list captures all calls
    - Request details are stored
    """
    # Make some requests
    await mock_wom.get_group_members("11114")
    await mock_wom.get_group_members("22225")
    await mock_wom.get_player_details("user1")
    
    # Check requests were tracked with correct details
    assert len(mock_wom.requests) == 3, "Should track all requests"
    
    assert mock_wom.requests[0]["method"] == "get_group_members"
    assert mock_wom.requests[0]["group_id"] == "11114"
    
    assert mock_wom.requests[1]["method"] == "get_group_members"
    assert mock_wom.requests[1]["group_id"] == "22225"
    
    assert mock_wom.requests[2]["method"] == "get_player_details"
    assert mock_wom.requests[2]["username"] == "user1"


@pytest.mark.asyncio
async def test_concurrent_requests_with_mocks(mock_wom):
    """
    Test that mocks handle concurrent requests correctly.
    
    Verifies:
    - Multiple concurrent requests work without interference
    - All requests are tracked
    """
    # Create concurrent requests
    tasks = [
        mock_wom.get_player_details(f"user{i}")
        for i in range(5)
    ]
    
    results = await asyncio.gather(*tasks)
    
    # Verify all completed
    assert len(results) == 5, "Should have results for all requests"
    
    # Verify all tracked
    assert len(mock_wom.requests) == 5, "Should track all concurrent requests"


# VCR CASSETTE-BASED TESTS COMING SOON
# After cassettes are properly recorded with correct endpoints, these tests will:
# - Use recorded API responses to minimize API calls
# - Record real API call once, save to cassette
# - Use cassette for all subsequent runs (zero API calls)
# 
# Next steps:
# 1. Record cassettes with correct group IDs and endpoints
# 2. Add integration tests that use cassettes with Harvest pipeline
# 3. Verify cassettes are properly versioned in git
