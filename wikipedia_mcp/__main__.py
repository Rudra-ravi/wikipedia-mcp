"""Main entry point for the Wikipedia MCP server."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from typing import Optional

from dotenv import load_dotenv

from wikipedia_mcp.auth_config import build_auth_config
from wikipedia_mcp.server import build_http_middleware, create_server

# Load environment variables from .env file if it exists
load_dotenv()


def _parse_locale_env() -> tuple[Optional[str], Optional[str]]:
    """Parse locale-related environment variables."""
    env_language = os.getenv("WIKIPEDIA_LANGUAGE")
    env_locale = os.getenv("WIKIPEDIA_LANGUAGE_REGION") or os.getenv("WIKIPEDIA_LOCALE")
    preferred_language = None
    preferred_country = None

    if env_locale:
        delimiter = "_" if "_" in env_locale else "-" if "-" in env_locale else None
        if delimiter:
            parts = env_locale.split(delimiter)
            if len(parts) == 2:
                preferred_language = parts[0].lower()
                preferred_country = parts[1].upper()
            else:
                preferred_language = env_locale.lower()
        else:
            preferred_language = env_locale.lower()

    if env_language and not preferred_language:
        preferred_language = env_language.lower()

    return preferred_language, preferred_country


def main() -> None:
    """Run the Wikipedia MCP server."""

    class LanguageAction(argparse.Action):
        def __call__(self, parser, namespace, values, option_string=None):
            setattr(namespace, self.dest, values)
            setattr(namespace, "_language_explicitly_set", True)

    preferred_language, preferred_country = _parse_locale_env()

    parser = argparse.ArgumentParser(
        description="Wikipedia MCP Server",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level",
    )
    parser.add_argument(
        "--transport",
        type=str,
        default="stdio",
        choices=["stdio", "http", "streamable-http", "sse"],
        help="Transport protocol (stdio for local clients, http/streamable-http for modern MCP, sse for legacy)",
    )
    parser.add_argument(
        "--path",
        type=str,
        default="/mcp",
        help="Endpoint path for HTTP/streamable-http transport (default: /mcp)",
    )
    parser.add_argument(
        "--language",
        "-l",
        type=str,
        default=preferred_language or "en",
        action=LanguageAction,
        help=(
            "Language code for Wikipedia (e.g., en, ja, es, zh-hans). "
            "Defaults to the WIKIPEDIA_LANGUAGE environment variable or 'en'."
        ),
    )
    parser.add_argument(
        "--country",
        "-c",
        type=str,
        default=preferred_country,
        help=(
            "Country/locale code for Wikipedia (e.g., US, CN, TW, Japan). "
            "Overrides --language if provided. See --list-countries for supported countries."
        ),
    )
    parser.add_argument(
        "--list-countries",
        action="store_true",
        help="List all supported country/locale codes and exit",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for network transports (default: 8000)",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host to bind network server to (default: 127.0.0.1, use 0.0.0.0 for all interfaces)",
    )
    parser.add_argument(
        "--enable-cache",
        action="store_true",
        help="Enable caching for Wikipedia API calls (optional)",
    )
    parser.add_argument(
        "--access-token",
        type=str,
        help=("Access token for Wikipedia API (optional). " "Can also be set via WIKIPEDIA_ACCESS_TOKEN."),
    )

    # MCP server auth options (separate from Wikipedia API token)
    parser.add_argument(
        "--auth-mode",
        type=str,
        choices=["none", "static", "jwt"],
        default=None,
        help="MCP transport auth mode for network transports (none|static|jwt)",
    )
    parser.add_argument(
        "--auth-token",
        type=str,
        default=None,
        help="Static Bearer token when --auth-mode static (or WIKIPEDIA_MCP_AUTH_TOKEN)",
    )
    parser.add_argument(
        "--auth-public-key",
        type=str,
        default=None,
        help="JWT public key (PEM) when --auth-mode jwt",
    )
    parser.add_argument(
        "--auth-jwks-uri",
        type=str,
        default=None,
        help="JWT JWKS URI when --auth-mode jwt",
    )
    parser.add_argument(
        "--auth-issuer",
        type=str,
        default=None,
        help="Expected JWT issuer when --auth-mode jwt",
    )
    parser.add_argument(
        "--auth-audience",
        type=str,
        default=None,
        help="Expected JWT audience when --auth-mode jwt",
    )
    parser.add_argument(
        "--auth-algorithm",
        type=str,
        default=None,
        help="JWT algorithm (default handled by auth provider)",
    )
    parser.add_argument(
        "--auth-required-scope",
        action="append",
        default=None,
        help="Required auth scope (repeatable) for JWT mode",
    )

    args = parser.parse_args()

    if args.list_countries:
        from wikipedia_mcp.wikipedia_client import WikipediaClient

        client = WikipediaClient()

        print("Supported Country/Locale Codes:")
        print("=" * 40)

        country_by_lang: dict[str, list[str]] = {}
        for country, lang in client.COUNTRY_TO_LANGUAGE.items():
            country_by_lang.setdefault(lang, []).append(country)

        for lang in sorted(country_by_lang.keys()):
            countries = country_by_lang[lang]
            examples = countries[:5]
            if len(countries) > 5:
                examples.append(f"... (+{len(countries) - 5} more)")
            print(f"{lang:>6}: {', '.join(examples)}")

        print("\nExamples:")
        print("  wikipedia-mcp --country US    # English (United States)")
        print("  wikipedia-mcp --country CN    # Chinese Simplified (China)")
        print("  wikipedia-mcp --country TW    # Chinese Traditional (Taiwan)")
        print("  wikipedia-mcp --country Japan # Japanese")
        return

    if args.country and getattr(args, "_language_explicitly_set", False):
        parser.error("Cannot specify both --language and --country. Use one or the other.")

    if not args.country and not getattr(args, "_language_explicitly_set", False):
        if preferred_country:
            args.country = preferred_country
            if preferred_language:
                args.language = preferred_language
        elif preferred_language:
            args.language = preferred_language

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stderr,
        force=True,
    )

    logger = logging.getLogger(__name__)

    is_network_transport = args.transport != "stdio"
    try:
        auth_config = build_auth_config(
            network_transport=is_network_transport,
            auth_mode=args.auth_mode,
            auth_token=args.auth_token,
            auth_public_key=args.auth_public_key,
            auth_jwks_uri=args.auth_jwks_uri,
            auth_issuer=args.auth_issuer,
            auth_audience=args.auth_audience,
            auth_algorithm=args.auth_algorithm,
            auth_required_scopes=args.auth_required_scope,
        )
    except ValueError as exc:
        parser.error(str(exc))

    access_token = args.access_token or os.getenv("WIKIPEDIA_ACCESS_TOKEN")

    try:
        server = create_server(
            language=args.language,
            country=args.country,
            enable_cache=args.enable_cache,
            access_token=access_token,
            auth_config=auth_config,
        )
    except ValueError as exc:
        logger.error("Configuration error: %s", exc)
        print(f"Error: {exc}")
        print("\nUse --list-countries to see supported country codes.")
        return

    if args.country:
        logger.info(
            "Starting Wikipedia MCP server with %s transport for country: %s",
            args.transport,
            args.country,
        )
    else:
        logger.info(
            "Starting Wikipedia MCP server with %s transport for language: %s",
            args.transport,
            args.language,
        )

    if auth_config.enabled:
        logger.info("Network auth mode enabled: %s", auth_config.mode)

    if args.transport in {"http", "streamable-http"}:
        http_middleware = build_http_middleware(auth_config)
        logger.info("Starting HTTP MCP server on %s:%d path=%s", args.host, args.port, args.path)
        server.run(
            transport="http",
            host=args.host,
            port=args.port,
            path=args.path,
            show_banner=False,
            middleware=http_middleware,
        )
        return

    if args.transport == "sse":
        http_middleware = build_http_middleware(auth_config)
        logger.warning("SSE transport is legacy; prefer --transport http or --transport streamable-http")
        logger.info("Starting SSE server on %s:%d", args.host, args.port)
        server.run(
            transport="sse",
            host=args.host,
            port=args.port,
            show_banner=False,
            middleware=http_middleware,
        )
        return

    logger.info("Using stdio transport - suppressing direct stdout messages for MCP communication.")
    logger.info("To use with Claude Desktop, ensure 'wikipedia-mcp' command is in your claude_desktop_config.json.")
    server.run(transport="stdio", show_banner=False)


if __name__ == "__main__":
    main()
