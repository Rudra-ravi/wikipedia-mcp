# Command Line Interface (CLI)

This document describes the `wikipedia-mcp` command-line options and usage.

## Synopsis

```bash
wikipedia-mcp [--transport stdio|http|streamable-http|sse] [--path <endpoint>] \
              [--language <code>] [--country <code|name>] [--list-countries] \
              [--host <host>] [--port <port>] [--enable-cache] \
              [--access-token <token>] \
              [--auth-mode none|static|jwt] [--auth-token <token>] \
              [--auth-public-key <pem>] [--auth-jwks-uri <uri>] \
              [--auth-issuer <issuer>] [--auth-audience <aud>] \
              [--auth-algorithm <alg>] [--auth-required-scope <scope>] \
              [--log-level LEVEL]
```

## Options

- `--transport` (default: `stdio`, choices: `stdio`, `http`, `streamable-http`, `sse`):
  - `stdio`: Recommended for local desktop clients (Claude Desktop, etc.)
  - `http` / `streamable-http`: Modern MCP network transport
  - `sse`: Legacy transport retained for compatibility
- `--path` (default: `/mcp`): Endpoint path for `http` / `streamable-http`.
- `--language, -l` (default: `en`): Wikipedia language code. Supports variants like `zh-hans`, `zh-tw`, `sr-latn`.
- `--country, -c`: Country/locale code or name (e.g., `US`, `CN`, `TW`, `Japan`). Overrides `--language`.
- `--list-countries`: Print supported country/locale mappings and exit.
- `--host` (default: `127.0.0.1`): Bind host for network transports.
- `--port` (default: `8000`): Bind port for network transports.
- `--enable-cache`: Enable in-process LRU caching for Wikipedia API calls.
- `--access-token`: Wikipedia API token (client-side Wikipedia request auth). Also supports `WIKIPEDIA_ACCESS_TOKEN`.

### MCP Server Transport Auth (`--auth-*`)

These options secure incoming MCP requests on network transports and are separate from `--access-token`.

- `--auth-mode` (`none|static|jwt`, default: `none`)
- `--auth-token`: Required for `--auth-mode static`
- `--auth-public-key`: JWT public key (PEM) for `--auth-mode jwt`
- `--auth-jwks-uri`: JWKS URL for `--auth-mode jwt`
- `--auth-issuer`, `--auth-audience`, `--auth-algorithm`: Optional JWT validation constraints
- `--auth-required-scope`: Repeatable scope requirement for JWT mode

Environment variable equivalents are supported via `WIKIPEDIA_MCP_AUTH_*`.

## Examples

```bash
# Default: stdio transport for Claude Desktop
wikipedia-mcp

# Modern network transport
wikipedia-mcp --transport http --host 0.0.0.0 --port 8080 --path /mcp

# Legacy SSE transport (compatibility mode)
wikipedia-mcp --transport sse --host 0.0.0.0 --port 8080

# Language and country selection
wikipedia-mcp --language zh-hans
wikipedia-mcp --country Taiwan

# Static bearer protection for network transport
wikipedia-mcp --transport http --auth-mode static --auth-token supersecret

# JWT auth using JWKS
wikipedia-mcp --transport http --auth-mode jwt --auth-jwks-uri https://issuer.example/.well-known/jwks.json --auth-issuer https://issuer.example

# Wikipedia API token (outbound requests)
wikipedia-mcp --enable-cache --access-token $WIKIPEDIA_ACCESS_TOKEN
```

## Behavior Notes

- Setting both `--language` and `--country` is disallowed when language is explicitly set.
- In stdio mode, stdout must remain protocol-clean; logs are sent to stderr.
- `sse` is retained for compatibility and considered legacy for new deployments.
- Authentication options are applied only to network transports.

## Exit Codes

- `0`: Successful startup (or expected stdio exit in non-interactive test contexts)
- Non-zero: Argument/configuration errors

## See Also

- `docs/API.md` for tool and resource contracts
- `docs/ARCHITECTURE.md` for transport/auth architecture
- `README.md` for installation and integration
