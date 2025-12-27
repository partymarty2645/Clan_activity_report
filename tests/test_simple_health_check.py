import pytest
import sys
import os
from unittest.mock import patch, MagicMock

# Ensure scripts can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts import db_health_check

class TestSimpleDBHealthCheck:
    @patch('sqlite3.connect')
    @patch('os.path.exists')
    def test_check_success(self, mock_exists, mock_connect):
        mock_exists.return_value = True
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        # Mock table counts (3 tables + user count)
        # Order: clan_members, wom_snapshots, discord_messages, partymarty94
        mock_cursor.fetchone.side_effect = [
            [10], [10], [10], [10]
        ]
        
        with patch('builtins.print'):
            result = db_health_check.check()
            assert result is True

    @patch('os.path.exists')
    def test_missing_db(self, mock_exists):
        mock_exists.return_value = False
        with patch('builtins.print'):
            result = db_health_check.check()
            assert result is False
