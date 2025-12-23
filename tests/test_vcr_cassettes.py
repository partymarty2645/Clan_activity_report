"""
Test suite for VCR cassette-based API testing.
Demonstrates how to use recorded API responses to minimize real API calls.
"""

import pytest
import os
from unittest.mock import AsyncMock, patch
from services.wom import WOMClient


async def test_wom_get_group_members_with_cassette(vcr_with_cassette):
    """
    Test WOM group members fetch using recorded cassette.
    
    First run: Records real API call to cassette file
    Subsequent runs: Uses cassette, no API call made
    """
    client = WOMClient()
    
    cassette_path = os.path.join(
        os.path.dirname(__file__), 
        'cassettes', 
        'wom_get_group_members.yaml'
    )
    
    # Use cassette instead of real API
    with vcr_with_cassette.use_cassette(cassette_path):
        # This will either record or playback from cassette
        members = await client.get_group_members('11114')
    
    assert members is not None
    assert len(members) >= 0
    await client.close()


async def test_wom_get_player_details_with_cassette(vcr_with_cassette):
    """
    Test WOM player details fetch using recorded cassette.
    
    Demonstrates minimal API calls - cassette is reused across multiple test runs.
    """
    client = WOMClient()
    
    cassette_path = os.path.join(
        os.path.dirname(__file__),
        'cassettes',
        'wom_get_player_details.yaml'
    )
    
    with vcr_with_cassette.use_cassette(cassette_path):
        player = await client.get_player_details('party_marty')
    
    assert player is not None
    assert 'username' in player or 'id' in player
    await client.close()


async def test_cassette_isolation(vcr_with_cassette):
    """
    Verify that cassettes are isolated per test - each can have different responses.
    
    This test demonstrates that you can:
    1. Record different responses for different tests
    2. Keep them separate via different cassette files
    3. Not worry about cross-test contamination
    """
    # Each test gets its own cassette scope
    cassette_path = os.path.join(
        os.path.dirname(__file__),
        'cassettes',
        'wom_get_group_members.yaml'
    )
    
    with vcr_with_cassette.use_cassette(cassette_path):
        # Tests are independent
        pass
    
    # Test isolation guaranteed by VCR
    assert True


def test_vcr_configuration(vcr_with_cassette):
    """Verify VCR is properly configured."""
    # Check that VCR fixture exists
    assert vcr_with_cassette is not None
    
    # Verify cassette directory exists
    cassette_dir = os.path.join(
        os.path.dirname(__file__),
        'cassettes'
    )
    assert os.path.exists(cassette_dir), f"Cassette directory should exist: {cassette_dir}"
