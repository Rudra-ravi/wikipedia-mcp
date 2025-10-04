"""
Tests for Personal Access Token functionality.
"""

import os
import pytest
from unittest.mock import Mock, patch, call
from wikipedia_mcp.wikipedia_client import WikipediaClient
from wikipedia_mcp.server import create_server


class TestAccessTokenClient:
    """Test WikipediaClient with access token functionality."""

    def test_client_init_without_token(self):
        """Test client initialization without access token."""
        client = WikipediaClient()
        assert client.access_token is None

    def test_client_init_with_token(self):
        """Test client initialization with access token."""
        token = "test_token_123"
        client = WikipediaClient(access_token=token)
        assert client.access_token == token

    def test_get_request_headers_without_token(self):
        """Test request headers without access token."""
        client = WikipediaClient()
        headers = client._get_request_headers()

        assert "User-Agent" in headers
        assert "Authorization" not in headers

    def test_get_request_headers_with_token(self):
        """Test request headers with access token."""
        token = "test_token_123"
        client = WikipediaClient(access_token=token)
        headers = client._get_request_headers()

        assert "User-Agent" in headers
        assert "Authorization" in headers
        assert headers["Authorization"] == f"Bearer {token}"

    @patch("wikipedia_mcp.wikipedia_client.requests.get")
    def test_search_uses_auth_headers(self, mock_get):
        """Test that search method uses authentication headers when token is provided."""
        token = "test_token_123"
        client = WikipediaClient(access_token=token)

        # Mock successful response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "query": {
                "search": [
                    {
                        "title": "Test Article",
                        "snippet": "Test snippet",
                        "pageid": 123,
                        "wordcount": 100,
                        "timestamp": "2023-01-01T00:00:00Z",
                    }
                ]
            }
        }
        mock_get.return_value = mock_response

        # Perform search
        client.search("test query")

        # Verify request was made with auth headers
        mock_get.assert_called_once()
        call_args = mock_get.call_args

        # Check that headers include authorization
        headers = call_args[1]["headers"]
        assert "Authorization" in headers
        assert headers["Authorization"] == f"Bearer {token}"

    @patch("wikipedia_mcp.wikipedia_client.requests.get")
    def test_get_coordinates_uses_auth_headers(self, mock_get):
        """Test that get_coordinates method uses authentication headers when token is provided."""
        token = "test_token_123"
        client = WikipediaClient(access_token=token)

        # Mock successful response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "query": {
                "pages": {
                    "123": {
                        "pageid": 123,
                        "title": "Test Article",
                        "coordinates": [
                            {
                                "lat": 40.7128,
                                "lon": -74.0060,
                                "primary": True,
                                "globe": "earth",
                            }
                        ],
                    }
                }
            }
        }
        mock_get.return_value = mock_response

        # Perform get_coordinates
        client.get_coordinates("Test Article")

        # Verify request was made with auth headers
        mock_get.assert_called_once()
        call_args = mock_get.call_args

        # Check that headers include authorization
        headers = call_args[1]["headers"]
        assert "Authorization" in headers
        assert headers["Authorization"] == f"Bearer {token}"

    def test_token_not_logged(self, caplog):
        """Test that access token is not logged for security."""
        import logging

        caplog.set_level(logging.DEBUG)

        token = "secret_token_123"
        WikipediaClient(access_token=token)

        # Check that token doesn't appear in logs
        for record in caplog.records:
            assert token not in record.getMessage()


class TestAccessTokenServer:
    """Test server creation with access token."""

    def test_create_server_without_token(self):
        """Test server creation without access token."""
        server = create_server()
        assert server is not None

    def test_create_server_with_token(self):
        """Test server creation with access token."""
        token = "test_token_123"
        server = create_server(access_token=token)
        assert server is not None


class TestAccessTokenCLI:
    """Test CLI argument and environment variable handling."""

    @patch("wikipedia_mcp.__main__.create_server")
    @patch("sys.argv", ["wikipedia-mcp", "--access-token", "cli_token_123"])
    def test_cli_access_token_argument(self, mock_create_server):
        """Test CLI access token argument is passed to server."""
        from wikipedia_mcp.__main__ import main

        # Mock server to avoid actually starting it
        mock_server = Mock()
        mock_create_server.return_value = mock_server
        mock_server.run = Mock()

        try:
            main()
        except SystemExit:
            pass  # Expected when server.run() is mocked

        # Verify create_server was called with the token
        mock_create_server.assert_called_once()
        call_args = mock_create_server.call_args
        assert call_args[1]["access_token"] == "cli_token_123"

    @patch("wikipedia_mcp.__main__.create_server")
    @patch("sys.argv", ["wikipedia-mcp"])
    @patch.dict(os.environ, {"WIKIPEDIA_ACCESS_TOKEN": "env_token_123"})
    def test_cli_environment_variable(self, mock_create_server):
        """Test environment variable is used when CLI argument not provided."""
        from wikipedia_mcp.__main__ import main

        # Mock server to avoid actually starting it
        mock_server = Mock()
        mock_create_server.return_value = mock_server
        mock_server.run = Mock()

        try:
            main()
        except SystemExit:
            pass  # Expected when server.run() is mocked

        # Verify create_server was called with the env var token
        mock_create_server.assert_called_once()
        call_args = mock_create_server.call_args
        assert call_args[1]["access_token"] == "env_token_123"

    @patch("wikipedia_mcp.__main__.create_server")
    @patch("sys.argv", ["wikipedia-mcp", "--access-token", "cli_token_123"])
    @patch.dict(os.environ, {"WIKIPEDIA_ACCESS_TOKEN": "env_token_123"})
    def test_cli_argument_overrides_environment(self, mock_create_server):
        """Test CLI argument takes priority over environment variable."""
        from wikipedia_mcp.__main__ import main

        # Mock server to avoid actually starting it
        mock_server = Mock()
        mock_create_server.return_value = mock_server
        mock_server.run = Mock()

        try:
            main()
        except SystemExit:
            pass  # Expected when server.run() is mocked

        # Verify create_server was called with CLI token, not env var
        mock_create_server.assert_called_once()
        call_args = mock_create_server.call_args
        assert call_args[1]["access_token"] == "cli_token_123"

    @patch("wikipedia_mcp.__main__.create_server")
    @patch("sys.argv", ["wikipedia-mcp"])
    def test_cli_no_token_provided(self, mock_create_server):
        """Test no token is passed when neither CLI arg nor env var is set."""
        from wikipedia_mcp.__main__ import main

        # Mock server to avoid actually starting it
        mock_server = Mock()
        mock_create_server.return_value = mock_server
        mock_server.run = Mock()

        # Ensure env var is not set
        if "WIKIPEDIA_ACCESS_TOKEN" in os.environ:
            del os.environ["WIKIPEDIA_ACCESS_TOKEN"]

        try:
            main()
        except SystemExit:
            pass  # Expected when server.run() is mocked

        # Verify create_server was called with None token
        mock_create_server.assert_called_once()
        call_args = mock_create_server.call_args
        assert call_args[1]["access_token"] is None


class TestAccessTokenSecurity:
    """Test security aspects of access token handling."""

    def test_token_in_repr(self):
        """Test that token doesn't appear in object representation."""
        token = "secret_token_123"
        client = WikipediaClient(access_token=token)

        # Check that token doesn't appear in string representation
        client_str = str(client)
        assert token not in client_str

        client_repr = repr(client)
        assert token not in client_repr

    @patch("wikipedia_mcp.wikipedia_client.requests.get")
    def test_error_logging_no_token_exposure(self, mock_get, caplog):
        """Test that errors don't expose the access token."""
        import logging

        caplog.set_level(logging.ERROR)

        token = "secret_token_123"
        client = WikipediaClient(access_token=token)

        # Mock request to raise an exception
        mock_get.side_effect = Exception("API Error")

        # Perform search that will fail
        client.search("test query")

        # Check that token doesn't appear in error logs
        for record in caplog.records:
            assert token not in record.getMessage()
