"""
Tests for Wikipedia table extraction functionality.
"""

import asyncio
from unittest.mock import Mock, patch

from wikipedia_mcp.wikipedia_client import _WikiTableParser, WikipediaClient
from wikipedia_mcp.server import create_server
from tests.tool_helpers import get_tool, get_tools


SAMPLE_HTML = """
<div>
<table class="infobox vcard"><tr><th>Info</th></tr><tr><td>skip me</td></tr></table>
<div class="mw-heading mw-heading2"><h2 id="Demographics">Demographics</h2>
<span class="mw-editsection">[edit]</span></div>
<table class="wikitable">
<caption>Populations [1]</caption>
<tr><th>City</th><th>Country</th><th>Pop</th></tr>
<tr><td>Paris</td><td>France</td><td>2,000,000[2]</td></tr>
<tr><td rowspan="2">Big</td><td>A</td><td>1</td></tr>
<tr><td>B</td><td>2</td></tr>
<tr><td colspan="2">Spanning</td><td>x</td></tr>
</table>
</div>
"""


def _mock_parse_response(html: str) -> Mock:
    mock_response = Mock()
    mock_response.raise_for_status.return_value = None
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "parse": {"title": "Test Article", "text": html}
    }
    return mock_response


class TestWikiTableParser:
    """Unit tests for the standalone HTML table parser."""

    def test_colspan_expansion(self):
        parser = _WikiTableParser()
        parser.feed('<table><tr><td colspan="2">A</td><td>B</td></tr></table>')
        assert parser.tables[0]["rows"][0] == [("A", False), ("A", False), ("B", False)]

    def test_rowspan_carry_over(self):
        parser = _WikiTableParser()
        parser.feed(
            '<table><tr><td rowspan="2">X</td><td>1</td></tr><tr><td>2</td></tr></table>'
        )
        rows = parser.tables[0]["rows"]
        assert rows[0] == [("X", False), ("1", False)]
        assert rows[1] == [("X", False), ("2", False)]

    def test_reference_markers_stripped(self):
        parser = _WikiTableParser()
        parser.feed("<table><tr><td>Value[1][note 2]</td></tr></table>")
        assert parser.tables[0]["rows"][0] == [("Value", False)]

    def test_section_attribution(self):
        parser = _WikiTableParser()
        parser.feed(
            "<table><tr><td>lead</td></tr></table>"
            '<div class="mw-heading"><h2 id="H">History</h2><span class="mw-editsection">[edit]</span></div>'
            "<table><tr><td>hist</td></tr></table>"
            "<h3>Early</h3><table><tr><td>early</td></tr></table>"
        )
        assert parser.tables[0]["section"] == ""
        assert parser.tables[1]["section"] == "History"
        assert parser.tables[2]["section"] == "Early"

    def test_nested_tables_are_separate(self):
        parser = _WikiTableParser()
        parser.feed(
            "<table><tr><td>outer<table><tr><td>inner</td></tr></table></td></tr></table>"
        )
        # Inner table closes first, so it appears first in the results.
        classes = [t["rows"] for t in parser.tables]
        assert [("inner", False)] in classes[0]
        assert len(parser.tables) == 2


class TestWikipediaClientTables:
    """Test get_tables in WikipediaClient."""

    def setup_method(self):
        self.client = WikipediaClient(language="en")

    @patch("wikipedia_mcp.wikipedia_client.requests.get")
    def test_get_tables_success(self, mock_get):
        mock_get.return_value = _mock_parse_response(SAMPLE_HTML)

        result = self.client.get_tables("Test Article")

        # Verify the parse API was called correctly.
        call_args = mock_get.call_args
        assert call_args[0][0] == "https://en.wikipedia.org/w/api.php"
        params = call_args[1]["params"]
        assert params["action"] == "parse"
        assert params["page"] == "Test Article"

        assert result["exists"] is True
        # Only the wikitable is returned by default (infobox excluded).
        assert len(result["tables"]) == 1
        table = result["tables"][0]
        assert table["index"] == 0
        assert table["caption"] == "Populations"
        assert table["section"] == "Demographics"
        assert table["headers"] == ["City", "Country", "Pop"]
        assert table["rows"][0] == ["Paris", "France", "2,000,000"]
        assert table["rows"][1] == ["Big", "A", "1"]
        assert table["rows"][2] == ["Big", "B", "2"]
        assert table["rows"][3] == ["Spanning", "Spanning", "x"]

    @patch("wikipedia_mcp.wikipedia_client.requests.get")
    def test_get_tables_include_all(self, mock_get):
        mock_get.return_value = _mock_parse_response(SAMPLE_HTML)

        result = self.client.get_tables("Test Article", include_all_tables=True)
        assert len(result["tables"]) == 2

    @patch("wikipedia_mcp.wikipedia_client.requests.get")
    def test_get_tables_no_tables(self, mock_get):
        mock_get.return_value = _mock_parse_response("<p>No tables here.</p>")

        result = self.client.get_tables("Test Article")
        assert result["exists"] is True
        assert result["tables"] == []
        assert "message" in result

    @patch("wikipedia_mcp.wikipedia_client.requests.get")
    def test_get_tables_missing_page(self, mock_get):
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "error": {"code": "missingtitle", "info": "The page you specified doesn't exist."}
        }
        mock_get.return_value = mock_response

        result = self.client.get_tables("Nonexistent Article XYZ")
        assert result["exists"] is False
        assert result["tables"] == []
        assert "error" in result

    @patch("wikipedia_mcp.wikipedia_client.requests.get")
    def test_get_tables_request_failure(self, mock_get):
        import requests

        mock_get.side_effect = requests.exceptions.ConnectionError("boom")

        result = self.client.get_tables("Test Article")
        assert result["exists"] is False
        assert result["tables"] == []
        assert "error" in result

    @patch("wikipedia_mcp.wikipedia_client.requests.get")
    def test_get_tables_formatversion1_shape(self, mock_get):
        # formatversion=1 nests HTML under a "*" key.
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "parse": {"title": "Test Article", "text": {"*": SAMPLE_HTML}}
        }
        mock_get.return_value = mock_response

        result = self.client.get_tables("Test Article")
        assert len(result["tables"]) == 1


class TestListTables:
    """Test list_tables (a) listing and (b) entry counts."""

    def setup_method(self):
        self.client = WikipediaClient(language="en")

    @patch("wikipedia_mcp.wikipedia_client.requests.get")
    def test_list_tables(self, mock_get):
        mock_get.return_value = _mock_parse_response(SAMPLE_HTML)

        result = self.client.list_tables("Test Article")
        assert result["exists"] is True
        assert result["count"] == 1
        summary = result["tables"][0]
        assert summary["index"] == 0
        assert summary["caption"] == "Populations"
        # Section the table appears under.
        assert summary["section"] == "Demographics"
        assert summary["headers"] == ["City", "Country", "Pop"]
        # (b) number of entries (data rows).
        assert summary["row_count"] == 4
        assert summary["column_count"] == 3

    @patch("wikipedia_mcp.wikipedia_client.requests.get")
    def test_list_tables_include_all(self, mock_get):
        mock_get.return_value = _mock_parse_response(SAMPLE_HTML)
        result = self.client.list_tables("Test Article", include_all_tables=True)
        assert result["count"] == 2


class TestGetTable:
    """Test get_table (c) row/column access and (d) whole table."""

    def setup_method(self):
        self.client = WikipediaClient(language="en")

    @patch("wikipedia_mcp.wikipedia_client.requests.get")
    def test_whole_table(self, mock_get):
        mock_get.return_value = _mock_parse_response(SAMPLE_HTML)
        result = self.client.get_table("Test Article", table_index=0)
        assert result["table_index"] == 0
        assert result["section"] == "Demographics"
        assert result["headers"] == ["City", "Country", "Pop"]
        assert result["row_count"] == 4
        assert result["column_count"] == 3
        assert result["rows"][0] == ["Paris", "France", "2,000,000"]

    @patch("wikipedia_mcp.wikipedia_client.requests.get")
    def test_single_row(self, mock_get):
        mock_get.return_value = _mock_parse_response(SAMPLE_HTML)
        result = self.client.get_table("Test Article", row=0)
        assert result["row_index"] == 0
        assert result["row"] == ["Paris", "France", "2,000,000"]
        assert "rows" not in result

    @patch("wikipedia_mcp.wikipedia_client.requests.get")
    def test_single_column_by_name(self, mock_get):
        mock_get.return_value = _mock_parse_response(SAMPLE_HTML)
        result = self.client.get_table("Test Article", column="Country")
        assert result["column_index"] == 1
        assert result["header"] == "Country"
        assert result["values"] == ["France", "A", "B", "Spanning"]

    @patch("wikipedia_mcp.wikipedia_client.requests.get")
    def test_single_column_by_index(self, mock_get):
        mock_get.return_value = _mock_parse_response(SAMPLE_HTML)
        result = self.client.get_table("Test Article", column="0")
        assert result["column_index"] == 0
        assert result["values"] == ["Paris", "Big", "Big", "Spanning"]

    @patch("wikipedia_mcp.wikipedia_client.requests.get")
    def test_single_cell(self, mock_get):
        mock_get.return_value = _mock_parse_response(SAMPLE_HTML)
        result = self.client.get_table("Test Article", row=0, column="Pop")
        assert result["row_index"] == 0
        assert result["column_index"] == 2
        assert result["value"] == "2,000,000"

    @patch("wikipedia_mcp.wikipedia_client.requests.get")
    def test_table_index_out_of_range(self, mock_get):
        mock_get.return_value = _mock_parse_response(SAMPLE_HTML)
        result = self.client.get_table("Test Article", table_index=5)
        assert "error" in result
        assert "out of range" in result["error"]

    @patch("wikipedia_mcp.wikipedia_client.requests.get")
    def test_row_out_of_range(self, mock_get):
        mock_get.return_value = _mock_parse_response(SAMPLE_HTML)
        result = self.client.get_table("Test Article", row=99)
        assert "error" in result

    @patch("wikipedia_mcp.wikipedia_client.requests.get")
    def test_unknown_column(self, mock_get):
        mock_get.return_value = _mock_parse_response(SAMPLE_HTML)
        result = self.client.get_table("Test Article", column="Nope")
        assert "error" in result
        assert "not found" in result["error"]


class TestTablesTool:
    """Test the get_tables MCP tool registration and invocation."""

    def test_tool_registered(self):
        server = create_server()

        async def gather_tools():
            return list((await get_tools(server)).keys())

        names = asyncio.run(gather_tools())
        for name in ("get_tables", "list_tables", "get_table"):
            assert name in names
            assert f"wikipedia_{name}" in names

    @patch("wikipedia_mcp.wikipedia_client.requests.get")
    def test_tool_invocation(self, mock_get):
        mock_get.return_value = _mock_parse_response(SAMPLE_HTML)
        server = create_server()

        async def call():
            tool = await get_tool(server, "get_tables")
            return tool.fn(title="Test Article")

        result = asyncio.run(call())
        assert result["exists"] is True
        assert result["tables"][0]["headers"] == ["City", "Country", "Pop"]

    @patch("wikipedia_mcp.wikipedia_client.requests.get")
    def test_get_table_tool_invocation(self, mock_get):
        mock_get.return_value = _mock_parse_response(SAMPLE_HTML)
        server = create_server()

        async def call():
            tool = await get_tool(server, "get_table")
            return tool.fn(title="Test Article", column="City")

        result = asyncio.run(call())
        assert result["header"] == "City"
        assert result["values"] == ["Paris", "Big", "Big", "Spanning"]
