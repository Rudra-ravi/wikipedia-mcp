# Architecture Overview

This document describes the high-level architecture and data flow of the Wikipedia MCP server.

## Components

- **CLI (`wikipedia_mcp/__main__.py`)**: Parses arguments, configures logging, initializes and starts the server.
- **Server (`wikipedia_mcp/server.py`)**: Creates a `FastMCP` instance, registers tools and MCP resources, and wires them to the client.
- **Wikipedia Client (`wikipedia_mcp/wikipedia_client.py`)**: Encapsulates interaction with Wikipedia API, language/country resolution, variant handling, caching, and error handling.
- **Examples (`examples/`)**: Demonstrates MCP client usage against the server.
- **Tests (`tests/`)**: Unit and integration tests for CLI, server, and client.

## Data Flow

1. A request arrives via MCP tool call or MCP resource path.
2. The server routes the request to a registered handler.
3. The handler delegates to `WikipediaClient` to perform API calls and assemble data.
4. Results are returned to the caller with structured fields.

## Language and Country Resolution

- Users specify either `--language` or `--country`.
- Country codes/names map to language or variant (e.g., `CN` → `zh-hans`, `TW` → `zh-tw`).
- Variants are parsed into base language plus variant flag for Wikipedia API; variant is added to request params when supported.

## Caching

- Optional LRU cache (`--enable-cache`) wraps selected client methods: search, get_article, get_summary, get_sections, get_links, get_related_topics, summarize_for_query, summarize_section, extract_facts, get_coordinates.
- Cache size is limited to avoid unbounded memory growth.

## Transports

- `stdio`: Default for Claude Desktop; logs to stderr, avoids stdout interference.
- `sse`: HTTP Server-Sent Events; bind with `--host` and `--port`. Use a reverse proxy for auth if exposing publicly.

## Tools and Resources

- Tools: `search_wikipedia`, `get_article`, `get_summary`, `summarize_article_for_query`, `summarize_article_section`, `extract_key_facts`, `get_related_topics`, `get_sections`, `get_links`, `get_coordinates`, `test_wikipedia_connectivity`.
- Resources: `search/{query}`, `article/{title}`, `summary/{title}`, `sections/{title}`, `links/{title}`, `coordinates/{title}`, `summary/{title}/query/{query}/length/{max_length}`, `summary/{title}/section/{section_title}/length/{max_length}`, `facts/{title}/topic/{topic_within_article}/count/{count}`.

## Error Handling

- Client methods handle HTTP/network errors and return safe defaults with `error` fields where applicable.
- Search and connectivity tools provide diagnostics to aid troubleshooting.

## Security Considerations

- SSE transport does not implement built-in auth; protect with a reverse proxy, private network, or firewall.
- Optional `--access-token` allows authenticated requests where supported to mitigate rate limits.

## Extensibility

- New tools/resources can be added by extending `WikipediaClient` and registering with `FastMCP` in `server.py`.
- Keep schemas simple and compatible with strict function-calling clients (e.g., Google ADK).
