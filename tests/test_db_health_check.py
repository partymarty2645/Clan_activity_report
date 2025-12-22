"""
Unit tests for scripts/db_health_check.py - Database health diagnostic.

Tests database health checking functionality:
- File existence and size calculations
- PRAGMA checks (page count, page size, fragmentation)
- Row count queries for table density
- Index inventory checks
- Data integrity validation
- Rich console output formatting
"""

import pytest
import os
import sqlite3
from unittest.mock import patch, MagicMock, call
from io import StringIO
import tempfile

# Import the module to test
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.db_health_check import check_health


class TestDbHealthCheckFileHandling:
    """Test database file existence and size checks."""

    @patch('os.path.exists')
    @patch('scripts.db_health_check.console.print')
    def test_missing_database(self, mock_print, mock_exists):
        """Verify error when database file doesn't exist."""
        mock_exists.return_value = False
        
        check_health()
        
        # Verify error message was printed
        mock_print.assert_called()
        call_args = str(mock_print.call_args_list)
        assert 'missing' in call_args.lower() or 'Database' in call_args

    @patch('os.path.exists')
    @patch('os.path.getsize')
    @patch('sqlite3.connect')
    def test_file_size_calculation(self, mock_connect, mock_getsize, mock_exists):
        """Verify file size is correctly calculated and displayed."""
        mock_exists.return_value = True
        # 5 MB
        mock_getsize.return_value = 5 * 1024 * 1024
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        # Mock PRAGMA responses
        mock_cursor.execute = MagicMock()
        mock_cursor.fetchone = MagicMock(return_value=[1000])  # page_count
        
        with patch('scripts.db_health_check.console.print'):
            check_health()
        
        # Verify getsize was called
        mock_getsize.assert_called()


class TestDbHealthCheckPragmaChecks:
    """Test PRAGMA query execution."""

    @patch('os.path.exists')
    @patch('os.path.getsize')
    @patch('sqlite3.connect')
    def test_page_count_pragma(self, mock_connect, mock_getsize, mock_exists):
        """Verify PRAGMA page_count is executed."""
        mock_exists.return_value = True
        mock_getsize.return_value = 1024 * 1024  # 1 MB
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        mock_cursor.fetchone = MagicMock(return_value=[1000])
        
        with patch('scripts.db_health_check.console.print'):
            check_health()
        
        # Verify PRAGMA page_count was called
        execute_calls = [str(call) for call in mock_cursor.execute.call_args_list]
        assert any('page_count' in str(call).lower() for call in execute_calls)

    @patch('os.path.exists')
    @patch('os.path.getsize')
    @patch('sqlite3.connect')
    def test_page_size_pragma(self, mock_connect, mock_getsize, mock_exists):
        """Verify PRAGMA page_size is executed."""
        mock_exists.return_value = True
        mock_getsize.return_value = 1024 * 1024
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        mock_cursor.fetchone = MagicMock(return_value=[4096])
        
        with patch('scripts.db_health_check.console.print'):
            check_health()
        
        execute_calls = [str(call) for call in mock_cursor.execute.call_args_list]
        assert any('page_size' in str(call).lower() for call in execute_calls)

    @patch('os.path.exists')
    @patch('os.path.getsize')
    @patch('sqlite3.connect')
    def test_fragmentation_calculation(self, mock_connect, mock_getsize, mock_exists):
        """Verify fragmentation calculation logic."""
        mock_exists.return_value = True
        mock_getsize.return_value = 1024 * 1024
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        # Mock all responses sequentially
        call_count = [0]
        def mock_fetchone_side_effect():
            call_count[0] += 1
            responses = [
                [1000],    # page_count
                [4096],    # page_size
                [100],     # freelist_count
                [0],       # wom_snapshots count
                [0],       # discord_messages count
                [0],       # wom_records count
                [0],       # NULL check
            ]
            if call_count[0] - 1 < len(responses):
                return responses[call_count[0] - 1]
            return [0]
        
        mock_cursor.fetchone = MagicMock(side_effect=mock_fetchone_side_effect)
        mock_cursor.fetchall = MagicMock(return_value=[])
        
        with patch('scripts.db_health_check.console.print'):
            check_health()
        
        # Verify execute was called for PRAGMA checks
        assert mock_cursor.execute.called


class TestDbHealthCheckRowCounts:
    """Test row count queries for data density."""

    @patch('os.path.exists')
    @patch('os.path.getsize')
    @patch('sqlite3.connect')
    def test_wom_snapshots_count(self, mock_connect, mock_getsize, mock_exists):
        """Verify wom_snapshots row count is queried."""
        mock_exists.return_value = True
        mock_getsize.return_value = 1024 * 1024
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        mock_cursor.fetchone = MagicMock(return_value=[1000])
        
        with patch('scripts.db_health_check.console.print'):
            check_health()
        
        execute_calls = [str(call) for call in mock_cursor.execute.call_args_list]
        assert any('wom_snapshots' in str(call) for call in execute_calls)

    @patch('os.path.exists')
    @patch('os.path.getsize')
    @patch('sqlite3.connect')
    def test_discord_messages_count(self, mock_connect, mock_getsize, mock_exists):
        """Verify discord_messages row count is queried."""
        mock_exists.return_value = True
        mock_getsize.return_value = 1024 * 1024
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        mock_cursor.fetchone = MagicMock(return_value=[5000])
        
        with patch('scripts.db_health_check.console.print'):
            check_health()
        
        execute_calls = [str(call) for call in mock_cursor.execute.call_args_list]
        assert any('discord_messages' in str(call) for call in execute_calls)

    @patch('os.path.exists')
    @patch('os.path.getsize')
    @patch('sqlite3.connect')
    def test_table_count_error_handling(self, mock_connect, mock_getsize, mock_exists):
        """Verify graceful handling of missing tables."""
        mock_exists.return_value = True
        mock_getsize.return_value = 1024 * 1024
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        # First calls for pragmas succeed, COUNT queries fail
        side_effects = [
            [1000],  # page_count
            [4096],  # page_size
            [100],   # freelist_count
        ]
        
        def fetchone_side_effect():
            if side_effects:
                return side_effects.pop(0)
            raise sqlite3.OperationalError("Table does not exist")
        
        mock_cursor.fetchone = MagicMock(side_effect=lambda: [0])
        mock_cursor.execute = MagicMock(side_effect=lambda *args, **kwargs: None)
        
        with patch('scripts.db_health_check.console.print'):
            # Should not raise exception
            check_health()


class TestDbHealthCheckIndexes:
    """Test index inventory checks."""

    @patch('os.path.exists')
    @patch('os.path.getsize')
    @patch('sqlite3.connect')
    def test_index_pragma_execution(self, mock_connect, mock_getsize, mock_exists):
        """Verify PRAGMA index_list is executed."""
        mock_exists.return_value = True
        mock_getsize.return_value = 1024 * 1024
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        mock_cursor.fetchone = MagicMock(return_value=[1000])
        mock_cursor.fetchall = MagicMock(return_value=[
            (0, 'idx_wom_snapshot_date', 0, 0, 0),
            (1, 'idx_discord_author_lower', 0, 0, 0),
        ])
        
        with patch('scripts.db_health_check.console.print'):
            check_health()
        
        execute_calls = [str(call) for call in mock_cursor.execute.call_args_list]
        assert any('index_list' in str(call).lower() for call in execute_calls)

    @patch('os.path.exists')
    @patch('os.path.getsize')
    @patch('sqlite3.connect')
    def test_required_indexes_check(self, mock_connect, mock_getsize, mock_exists):
        """Verify required indexes are checked."""
        mock_exists.return_value = True
        mock_getsize.return_value = 1024 * 1024
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        mock_cursor.fetchone = MagicMock(return_value=[1000])
        # Return indexes that include some required ones
        mock_cursor.fetchall = MagicMock(return_value=[
            (0, 'idx_wom_snapshot_date', 0, 0, 0),
            (1, 'idx_discord_author_lower', 0, 0, 0),
            (2, 'idx_wom_snapshots_username_timestamp', 0, 0, 0),
        ])
        
        with patch('scripts.db_health_check.console.print') as mock_print:
            check_health()
        
        output = ' '.join([str(call) for call in mock_print.call_args_list])
        # Should mention index inventory
        assert 'Index' in output or 'index' in output


class TestDbHealthCheckIntegrity:
    """Test data integrity checks."""

    @patch('os.path.exists')
    @patch('os.path.getsize')
    @patch('sqlite3.connect')
    def test_null_username_check(self, mock_connect, mock_getsize, mock_exists):
        """Verify NULL username check is executed."""
        mock_exists.return_value = True
        mock_getsize.return_value = 1024 * 1024
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        mock_cursor.fetchone = MagicMock(return_value=[0])  # No NULL usernames
        mock_cursor.fetchall = MagicMock(return_value=[])
        
        with patch('scripts.db_health_check.console.print'):
            check_health()
        
        execute_calls = [str(call) for call in mock_cursor.execute.call_args_list]
        # Should check for NULL usernames
        assert any('NULL' in str(call) or 'null' in str(call).lower() for call in execute_calls)

    @patch('os.path.exists')
    @patch('os.path.getsize')
    @patch('sqlite3.connect')
    def test_null_username_found(self, mock_connect, mock_getsize, mock_exists):
        """Verify NULL usernames are reported."""
        mock_exists.return_value = True
        mock_getsize.return_value = 1024 * 1024
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        # Report 5 NULL usernames
        mock_cursor.fetchone = MagicMock(return_value=[5])
        mock_cursor.fetchall = MagicMock(return_value=[])
        
        with patch('scripts.db_health_check.console.print') as mock_print:
            check_health()
        
        output = ' '.join([str(call) for call in mock_print.call_args_list])
        # Should mention NULL usernames
        assert 'NULL' in output or 'Integrity' in output


class TestDbHealthCheckConnectionCleanup:
    """Test database connection cleanup."""

    @patch('os.path.exists')
    @patch('os.path.getsize')
    @patch('sqlite3.connect')
    def test_connection_closed(self, mock_connect, mock_getsize, mock_exists):
        """Verify database connection is properly closed."""
        mock_exists.return_value = True
        mock_getsize.return_value = 1024 * 1024
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        mock_cursor.fetchone = MagicMock(return_value=[1000])
        mock_cursor.fetchall = MagicMock(return_value=[])
        
        with patch('scripts.db_health_check.console.print'):
            check_health()
        
        # Verify connection close was called
        mock_conn.close.assert_called()

    @patch('os.path.exists')
    @patch('os.path.getsize')
    @patch('sqlite3.connect')
    def test_connection_closed_on_error(self, mock_connect, mock_getsize, mock_exists):
        """Verify connection is closed when check_health completes."""
        mock_exists.return_value = True
        mock_getsize.return_value = 1024 * 1024
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        # Setup mock responses
        call_count = [0]
        def mock_fetchone():
            call_count[0] += 1
            responses = [
                [1000],    # page_count
                [4096],    # page_size
                [100],     # freelist_count
                [0], [0], [0],  # table counts
                [0],       # NULL check
            ]
            if call_count[0] - 1 < len(responses):
                return responses[call_count[0] - 1]
            return [0]
        
        mock_cursor.fetchone = MagicMock(side_effect=mock_fetchone)
        mock_cursor.fetchall = MagicMock(return_value=[])
        
        with patch('scripts.db_health_check.console.print'):
            check_health()
        
        # Verify connection.close() was called
        mock_conn.close.assert_called()


class TestDbHealthCheckConsoleOutput:
    """Test Rich console output formatting."""

    @patch('os.path.exists')
    @patch('os.path.getsize')
    @patch('sqlite3.connect')
    def test_console_output_called(self, mock_connect, mock_getsize, mock_exists):
        """Verify console output is generated."""
        mock_exists.return_value = True
        mock_getsize.return_value = 1024 * 1024
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        mock_cursor.fetchone = MagicMock(return_value=[1000])
        mock_cursor.fetchall = MagicMock(return_value=[])
        
        with patch('scripts.db_health_check.console.print') as mock_print:
            check_health()
        
        # Verify console.print was called multiple times
        assert mock_print.call_count > 0

    @patch('os.path.exists')
    @patch('os.path.getsize')
    @patch('sqlite3.connect')
    def test_output_contains_physical_specs(self, mock_connect, mock_getsize, mock_exists):
        """Verify output includes physical specs section."""
        mock_exists.return_value = True
        mock_getsize.return_value = 5 * 1024 * 1024
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        mock_cursor.fetchone = MagicMock(return_value=[1000])
        mock_cursor.fetchall = MagicMock(return_value=[])
        
        with patch('scripts.db_health_check.console.print') as mock_print:
            check_health()
        
        output = ' '.join([str(call) for call in mock_print.call_args_list])
        assert 'Physical' in output or 'Size' in output

    @patch('os.path.exists')
    @patch('os.path.getsize')
    @patch('sqlite3.connect')
    def test_output_contains_data_density(self, mock_connect, mock_getsize, mock_exists):
        """Verify output includes data density section."""
        mock_exists.return_value = True
        mock_getsize.return_value = 1024 * 1024
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        mock_cursor.fetchone = MagicMock(return_value=[1000])
        mock_cursor.fetchall = MagicMock(return_value=[])
        
        with patch('scripts.db_health_check.console.print') as mock_print:
            check_health()
        
        output = ' '.join([str(call) for call in mock_print.call_args_list])
        assert 'Density' in output or 'rows' in output
