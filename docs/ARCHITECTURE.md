# Architecture Overview

This document describes the high-level architecture and data flow of the Wikipedia MCP server.

## Components

- **CLI (`wikipedia_mcp/__main__.py`)**: Parses runtime configuration, validates auth/transport options, configures logging, and launches the server.
- **Auth Config (`wikipedia_mcp/auth_config.py`)**: Validates `--auth-*` options and environment fallbacks into a transport auth config.
- **Server (`wikipedia_mcp/server.py`)**: Builds `FastMCP`, wires tool/resource handlers, configures JWT auth provider, and exposes static bearer middleware for network transports.
- **Schemas (`wikipedia_mcp/schemas.py`)**: Pydantic output models used to generate explicit MCP `outputSchema` definitions.
- **Wikipedia Client (`wikipedia_mcp/wikipedia_client.py`)**: Handles Wikipedia API interaction, language/country mapping, variants, retries, and JSON/error normalization.
- **Tests (`tests/`)**: Coverage for CLI behavior, tool schemas, auth modes, language/country handling, and compatibility contracts.

## Data Flow

1. A request arrives through MCP tool invocation or resource read.
2. FastMCP dispatches to a registered handler in `server.py`.
3. Handler calls `WikipediaClient` methods.
4. Client performs API/library operations and normalizes errors.
5. Handler returns structured output aligned with explicit `outputSchema`.

## Transport Model

- `stdio` (default): local integrations and desktop clients.
- `http` / `streamable-http`: preferred network deployment transport (endpoint path default `/mcp`).
- `sse`: legacy compatibility transport.

## Auth Model

Auth is only applied to network transports:

- `none`: no request auth.
- `static`: exact bearer token enforced by ASGI middleware.
- `jwt`: FastMCP `BearerAuthProvider` validates JWT using public key or JWKS.

This is separate from `--access-token`, which is used for outbound Wikipedia API requests.

## Tool Surface

- Canonical tools are preserved (`search_wikipedia`, `get_article`, etc.).
- Each canonical tool also has a discoverability alias prefixed with `wikipedia_`.
- Tools include MCP annotations (`readOnlyHint`, `idempotentHint`, `openWorldHint`, `destructiveHint`).

## Error Handling

- HTTP calls to Wikipedia use bounded retry/backoff on retryable failures.
- Non-JSON or malformed responses are normalized into actionable error payloads.
- Connectivity/search/coordinates surface safe fallback outputs instead of uncaught exceptions.

## Security Notes

- For exposed network transports, prefer `http` + `--auth-mode static|jwt` and private-network/reverse-proxy controls.
- Avoid logging secrets or bearer tokens.

## Extensibility

- Add new MCP tools in `server.py` and register matching alias + annotations.
- Add/extend output models in `schemas.py` to keep contracts explicit.
- Extend `WikipediaClient` with focused methods and keep protocol-facing adaptation in server handlers.
