# User Guide

This guide helps you install, configure, and use the Wikipedia MCP server effectively.

## Installation

- Recommended (Claude Desktop):
  ```bash
  pip install pipx && pipx ensurepath
  pipx install wikipedia-mcp
  ```
- PyPI:
  ```bash
  pip install wikipedia-mcp
  ```
- From source:
  ```bash
  git clone https://github.com/rudra-ravi/wikipedia-mcp.git
  cd wikipedia-mcp
  python3 -m venv venv && source venv/bin/activate
  pip install -e .
  ```

## Quick Start

- Run the server (stdio transport):
  ```bash
  wikipedia-mcp
  ```
- SSE transport:
  ```bash
  wikipedia-mcp --transport sse --host 0.0.0.0 --port 8080
  ```
- Select language or country:
  ```bash
  wikipedia-mcp --language zh-hans
  wikipedia-mcp --country Japan
  wikipedia-mcp --list-countries
  ```
- Enable caching and set token:
  ```bash
  export WIKIPEDIA_ACCESS_TOKEN=your_token
  wikipedia-mcp --enable-cache --access-token $WIKIPEDIA_ACCESS_TOKEN
  ```

## Using with Claude Desktop

Add to your Claude config (`claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "wikipedia": { "command": "wikipedia-mcp" }
  }
}
```
Use full path if needed. See `README.md` for platform-specific locations and variants.

## MCP Tools Overview

- `search_wikipedia(query, limit=10)`
- `get_article(title)`
- `get_summary(title)`
- `summarize_article_for_query(title, query, max_length=250)`
- `summarize_article_section(title, section_title, max_length=150)`
- `extract_key_facts(title, topic_within_article="", count=5)`
- `get_related_topics(title, limit=10)`
- `get_sections(title)`
- `get_links(title)`
- `get_coordinates(title)`
- `test_wikipedia_connectivity()`

See `docs/API.md` for full schemas and example responses.

## Example Workflow

1. Search:
   ```json
   {"tool":"search_wikipedia","arguments":{"query":"quantum computing","limit":3}}
   ```
2. Get summary for the first result title.
3. Get related topics and sections as needed.
4. Retrieve full article when required.

## Troubleshooting

- Empty search results:
  - Run `test_wikipedia_connectivity` to check network.
  - Verify query spelling and try broader terms.
- 403/rate limits:
  - Provide `--access-token` or set `WIKIPEDIA_ACCESS_TOKEN`.
  - Reduce request frequency.
- SSE exposure:
  - Protect with reverse proxy auth or restrict network access.
- Country/language conflicts:
  - Do not set both `--language` and `--country` simultaneously.

## FAQ

- Q: Does SSE expose HTTP endpoints publicly?
  - A: SSE transport exposes MCP resources; add your own reverse proxy and auth if needed.
- Q: How do language variants work?
  - A: The server connects to the base language and adds a `variant` param to requests when applicable.

## Support

Open issues at the repository or see the README for contact links.
