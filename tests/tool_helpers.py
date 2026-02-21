"""Test helpers for FastMCP tool introspection across FastMCP versions."""

from __future__ import annotations

import inspect
from typing import Any


async def get_tools(server: Any) -> dict[str, Any]:
    """Return a name->tool mapping for FastMCP 2.x and 3.x."""
    get_tools_fn = getattr(server, "get_tools", None)
    if callable(get_tools_fn):
        tools_result = get_tools_fn()
        if inspect.isawaitable(tools_result):
            tools_result = await tools_result

        if isinstance(tools_result, dict):
            return tools_result

        return {tool.name: tool for tool in tools_result}

    list_tools_fn = getattr(server, "list_tools", None)
    if not callable(list_tools_fn):
        raise AttributeError("Server does not expose get_tools() or list_tools()")

    tools_result = list_tools_fn()
    if inspect.isawaitable(tools_result):
        tools_result = await tools_result
    return {tool.name: tool for tool in tools_result}


async def get_tool(server: Any, name: str) -> Any:
    """Fetch a tool object by name for FastMCP 2.x and 3.x."""
    get_tool_fn = getattr(server, "get_tool", None)
    if callable(get_tool_fn):
        tool_result = get_tool_fn(name)
        if inspect.isawaitable(tool_result):
            return await tool_result
        return tool_result

    tools = await get_tools(server)
    return tools.get(name)
