"""Tests for the optional tool alias behaviour."""

import asyncio
from unittest.mock import MagicMock, patch

from wikipedia_mcp.server import create_server
from tests.tool_helpers import get_tools


def _names(server):
    return set(asyncio.run(get_tools(server)).keys())


def test_aliases_enabled_by_default():
    names = _names(create_server())
    assert "search_wikipedia" in names
    assert "wikipedia_search_wikipedia" in names


def test_aliases_can_be_disabled():
    names = _names(create_server(tool_aliases=False))
    assert "search_wikipedia" in names
    assert not any(n.startswith("wikipedia_") for n in names)
    assert len(names) == len(_names(create_server())) // 2


def _run_cli(argv, env=None):
    from wikipedia_mcp.__main__ import main

    server = MagicMock()
    with patch("wikipedia_mcp.__main__.create_server", return_value=server) as cs, patch(
        "sys.argv", ["wikipedia-mcp"] + argv
    ), patch.dict("os.environ", env or {}, clear=False):
        main()
    return cs.call_args.kwargs


def test_cli_flag_disables_aliases():
    assert _run_cli(["--no-tool-aliases"])["tool_aliases"] is False


def test_cli_env_disables_aliases():
    assert _run_cli([], {"WIKIPEDIA_TOOL_ALIASES": "false"})["tool_aliases"] is False


def test_cli_default_keeps_aliases():
    assert _run_cli([], {"WIKIPEDIA_TOOL_ALIASES": "true"})["tool_aliases"] is True
