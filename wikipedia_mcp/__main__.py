"""
Main entry point for the Wikipedia MCP server.
This script parses command-line arguments, reads optional environment variables,
configures logging, and then starts the Wikipedia MCP server.
"""

import argparse
import logging
import sys
import os
from typing import Optional
from dotenv import load_dotenv

from wikipedia_mcp.server import create_server

# Load environment variables from .env file if it exists
load_dotenv()


def _parse_locale_env() -> tuple[Optional[str], Optional[str]]:
    """
    Parse environment variables related to Wikipedia language and locale.

    Returns a tuple of (preferred_language, preferred_country). If only a
    language code is available, the second element will be None.
    Environment variables checked (in order):
      - WIKIPEDIA_LANGUAGE: explicit language code (e.g., "en", "de")
      - WIKIPEDIA_LANGUAGE_REGION: locale string (e.g., "en_US", "de-DE")
      - WIKIPEDIA_LOCALE: alias for language-region string

    Locale strings are split on '_' or '-' to extract language and country.
    """
    env_language = os.getenv("WIKIPEDIA_LANGUAGE")
    env_locale = os.getenv("WIKIPEDIA_LANGUAGE_REGION") or os.getenv("WIKIPEDIA_LOCALE")
    preferred_language = None
    preferred_country = None

    # Parse locale string into language and country if provided
    if env_locale:
        # Accept both underscore and hyphen delimiters
        delimiter = "_" if "_" in env_locale else "-" if "-" in env_locale else None
        if delimiter:
            parts = env_locale.split(delimiter)
            if len(parts) == 2:
                preferred_language = parts[0].lower()
                preferred_country = parts[1].upper()
            else:
                # If not split into two parts, treat the whole string as language
                preferred_language = env_locale.lower()
        else:
            preferred_language = env_locale.lower()

    # If explicit language env var is set and no language derived from locale, use it
    if env_language and not preferred_language:
        preferred_language = env_language.lower()

    return preferred_language, preferred_country


def main() -> None:
    """Run the Wikipedia MCP server."""

    class LanguageAction(argparse.Action):
        """
        Custom argparse action to flag when the language argument has been explicitly set.
        This allows us to distinguish between an explicit CLI argument and a default value
        when applying environment variable overrides.
        """

        def __call__(self, parser, namespace, values, option_string=None):
            setattr(namespace, self.dest, values)
            setattr(namespace, "_language_explicitly_set", True)

    # Determine preferred language and country from environment variables
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
        choices=["stdio", "sse"],
        help=(
            "Transport protocol for MCP communication "
            "(stdio for Claude Desktop, sse for HTTP streaming)"
        ),
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
            "Overrides --language if provided. See --list-countries for "
            "supported countries. Defaults to the country portion of "
            "WIKIPEDIA_LANGUAGE_REGION or WIKIPEDIA_LOCALE if set."
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
        help="Port for SSE transport (default: 8000, optional)",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host to bind SSE server to (default: 127.0.0.1, use 0.0.0.0 for all interfaces)",
    )
    parser.add_argument(
        "--enable-cache",
        action="store_true",
        help="Enable caching for Wikipedia API calls (optional)",
    )
    parser.add_argument(
        "--access-token",
        type=str,
        help=(
            "Access token for Wikipedia API (optional). "
            "Can also be set via the WIKIPEDIA_ACCESS_TOKEN environment variable."
        ),
    )

    args = parser.parse_args()

    # If user requested to list supported countries, do it and exit
    if args.list_countries:
        from wikipedia_mcp.wikipedia_client import WikipediaClient

        client = WikipediaClient()

        print("Supported Country/Locale Codes:")
        print("=" * 40)

        # Group by language for better readability
        country_by_lang = {}
        for country, lang in client.COUNTRY_TO_LANGUAGE.items():
            country_by_lang.setdefault(lang, []).append(country)

        # Sort languages and show examples
        for lang in sorted(country_by_lang.keys()):
            countries = country_by_lang[lang]
            # Show up to 5 country codes per language
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

    # Validate that both --language and --country are not provided when language is explicitly set
    if args.country and getattr(args, "_language_explicitly_set", False):
        print("Error: Cannot specify both --language and --country. Use one or the other.")
        parser.print_help()
        return

    # Apply environment overrides if user did not explicitly set language or country
    # Only override if there is a preferred value and the corresponding argument is not provided
    if not args.country and not getattr(args, "_language_explicitly_set", False):
        # Use preferred_country if available; if so, also set language
        if preferred_country:
            args.country = preferred_country
            if preferred_language:
                args.language = preferred_language
        elif preferred_language:
            args.language = preferred_language

    # Configure logging - use basicConfig for simplicity but ensure it goes to stderr
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stderr,
        force=True,  # Override any existing basicConfig
    )

    logger = logging.getLogger(__name__)

    # Determine the access token, favor CLI argument over environment variable
    access_token = args.access_token or os.getenv("WIKIPEDIA_ACCESS_TOKEN")

    # Create and start the server
    try:
        server = create_server(
            language=args.language,
            country=args.country,
            enable_cache=args.enable_cache,
            access_token=access_token,
        )
    except ValueError as e:
        # Handle misconfiguration errors (e.g., unsupported country codes)
        logger.error("Configuration error: %s", e)
        print(f"Error: {e}")
        print("\nUse --list-countries to see supported country codes.")
        return

    # Log startup information for clarity
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

    # Provide a configuration template for Claude Desktop if using non-stdio transport
    if args.transport != "stdio":
        config_template = """
        {
          "mcpServers": {
            "wikipedia": {
              "command": "wikipedia-mcp"
            }
          }
        }
        """
        logger.info(
            "To use with Claude Desktop, configure claude_desktop_config.json with:%s",
            config_template,
        )
    else:
        logger.info("Using stdio transport - suppressing direct stdout messages for MCP communication.")
        logger.info(
            "To use with Claude Desktop, ensure 'wikipedia-mcp' command is in your claude_desktop_config.json."
        )

    # Finally, run the server with the chosen transport
    if args.transport == "sse":
        logger.info("Starting SSE server on %s:%d", args.host, args.port)
        server.run(transport=args.transport, port=args.port, host=args.host)
    else:
        server.run(transport=args.transport)


if __name__ == "__main__":
    main()
