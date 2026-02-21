# Development Guide

This guide covers local setup, checks, and release-ready validation.

## Setup

```bash
git clone https://github.com/rudra-ravi/wikipedia-mcp.git
cd wikipedia-mcp
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Project Layout

```text
wikipedia-mcp/
├── docs/
├── examples/
├── tests/
├── wikipedia_mcp/
│   ├── __init__.py
│   ├── __main__.py
│   ├── auth_config.py
│   ├── schemas.py
│   ├── server.py
│   └── wikipedia_client.py
├── pyproject.toml
└── README.md
```

## Core Commands

```bash
# Lint + type-check
.venv/bin/python -m flake8 wikipedia_mcp tests
.venv/bin/python -m mypy wikipedia_mcp

# Tests
.venv/bin/python -m pytest tests/ -v

# Focused compatibility checks
.venv/bin/python -m pytest tests/test_google_adk_compatibility.py -v
```

## Coding Guidelines

- Keep tool names backward compatible; add aliases rather than renaming canonical tools.
- Use explicit `outputSchema` via models in `schemas.py` for MCP tools.
- Keep protocol-facing logic in `server.py`; keep Wikipedia API logic in `wikipedia_client.py`.
- Maintain stdio protocol cleanliness (no stdout writes for logs).

## Auth and Transport Notes

- `--access-token` is for Wikipedia API calls.
- `--auth-*` options secure inbound MCP network transports.
- Prefer `--transport http` (or `streamable-http`) for new network deployments.
- Keep `sse` changes compatibility-safe unless doing a planned major release.

## Release Checklist

1. Update version in `pyproject.toml` and `wikipedia_mcp/__init__.py`.
2. Add a clear changelog entry in `CHANGELOG.md`.
3. Run lint, mypy, and full test suite in `.venv`.
4. Build and verify package:

```bash
.venv/bin/python -m build
.venv/bin/python -m twine check dist/*
```

## Troubleshooting

- If tests fail only in system Python, ensure `.venv` is active and dependencies are installed there.
- If MCP startup fails, run with `--log-level DEBUG` and verify auth/transport combinations.
- If network tools return empty results, run `test_wikipedia_connectivity` first to isolate upstream/API failures.
