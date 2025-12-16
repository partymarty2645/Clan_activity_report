import asyncio
import sys
import unittest
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

# Add root dir to path
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), '..'))

# Mock imports so we don't need full env
sys.modules['core.config'] = MagicMock()
sys.modules['services.discord'] = MagicMock()
sys.modules['services.wom'] = MagicMock()
sys.modules['database.connector'] = MagicMock()
sys.modules['database.models'] = MagicMock()

# Now import the function to test
# We need to do some tricks because harvest.py imports at top level
with patch('services.wom.wom_client') as mock_wom, \
     patch('database.connector.SessionLocal') as mock_session_cls, \
     patch('database.connector.init_db') as mock_init:
    import harvest

class TestDeepScan(unittest.TestCase):
    def test_incremental_logic(self):
        # Setup
        mock_db = MagicMock()
        harvest.SessionLocal = MagicMock(return_value=mock_db)
        harvest.wom_client = MagicMock()
        harvest.console = MagicMock()
        
        # Test Case 1: No previous data
        # Mock DB returning None for latest timestamp
        mock_db.execute.return_value.scalar.return_value = None
        harvest.wom_client.get_player_snapshots =  MagicMock(return_value=asyncio.Future())
        harvest.wom_client.get_player_snapshots.return_value.set_result([])

        # Run
        try:
            members = [{'username': 'new_user'}]
            asyncio.run(harvest.process_wom_snapshots_deep(123, members))
            
            # Assert called with NO start_date
            harvest.wom_client.get_player_snapshots.assert_called_with('new_user', start_date=None)
        except AssertionError as e:
            print(f"Assertion Failed! Calls: {harvest.wom_client.get_player_snapshots.call_args_list}")
            raise e
        
        # Test Case 2: Has previous data
        harvest.wom_client.get_player_snapshots.reset_mock()
        # Mock DB returning a datetime
        last_seen = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_db.execute.return_value.scalar.return_value = last_seen
        
        # Run
        members = [{'username': 'old_user'}]
        asyncio.run(harvest.process_wom_snapshots_deep(123, members))
        
        # Assert called WITH start_date = last_seen + 1s
        expected_start = (last_seen + timedelta(seconds=1)).isoformat()
        harvest.wom_client.get_player_snapshots.assert_called_with('old_user', start_date=expected_start)
        
        print("Verification Passed: Logic correctly handles new vs existing users.")

if __name__ == '__main__':
    t = TestDeepScan()
    t.test_incremental_logic()
