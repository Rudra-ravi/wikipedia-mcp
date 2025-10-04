# Command Line Interface (CLI)

This document describes the `wikipedia-mcp` command-line options and usage.

## Synopsis

```bash
wikipedia-mcp [--transport stdio|sse] [--language <code>] [--country <code|name>] \
              [--list-countries] [--host <host>] [--port <port>] \
              [--enable-cache] [--access-token <token>] [--log-level LEVEL]
```

## Options

- `--transport` (default: `stdio`, choices: `stdio`, `sse`):
  - `stdio`: Use stdio transport (recommended for Claude Desktop)
  - `sse`: Start an HTTP SSE server (configure `--host` and `--port`)
- `--language, -l` (default: `en`): Wikipedia language code. Supports variants like `zh-hans`, `zh-tw`, `sr-latn`, etc.
- `--country, -c`: Country/locale code or name (e.g., `US`, `CN`, `TW`, `Japan`). Overrides `--language` if provided.
- `--list-countries`: Print all supported country/locale mappings and exit.
- `--host` (default: `127.0.0.1`): Host to bind when `--transport sse`.
- `--port` (default: `8000`): Port to bind when `--transport sse`.
- `--enable-cache`: Enable in-process LRU caching for Wikipedia API calls.
- `--access-token`: Personal Access Token for Wikipedia API (optional) to raise rate limits. May also be set via `WIKIPEDIA_ACCESS_TOKEN` environment variable.
- `--log-level` (default: `INFO`, choices: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`): Logging verbosity.

## Examples

```bash
# Default: stdio transport for Claude Desktop
wikipedia-mcp

# SSE transport for HTTP streaming
wikipedia-mcp --transport sse --host 0.0.0.0 --port 8080

# Language-based selection
wikipedia-mcp --language zh-hans
wikipedia-mcp --language sr-latn

# Country/locale selection (overrides language)
wikipedia-mcp --country US
wikipedia-mcp --country China
wikipedia-mcp --country Taiwan

# List supported countries/regions
wikipedia-mcp --list-countries

# Enable caching and provide a token
wikipedia-mcp --enable-cache --access-token $WIKIPEDIA_ACCESS_TOKEN

# Debug logs
wikipedia-mcp --log-level DEBUG
```

## Behavior Notes

- Specifying both `--language` and `--country` is disallowed when `--language` is explicitly set. Use one or the other.
- When `--country` is provided, it maps to an appropriate language or variant automatically (e.g., `CN` → `zh-hans`, `TW` → `zh-tw`).
- In stdio mode, stdout is intentionally kept empty to avoid interfering with the MCP protocol; logs go to stderr.
- SSE transport uses Uvicorn under the hood and will block the process to serve requests.

## Environment Variables

- `WIKIPEDIA_ACCESS_TOKEN`: Optional Personal Access Token to authenticate requests to the Wikipedia API endpoints that support it; improves rate limits and mitigates 403s.

## Exit Codes

- `0`: Successful startup (stdio mode exits cleanly in test environments)
- Non-zero: Argument errors or configuration issues

## See Also

- `docs/API.md` for tool and resource documentation
- `README.md` for installation and integration guidance
