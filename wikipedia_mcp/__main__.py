"""
Main entry point for the Wikipedia MCP server.
"""

import argparse
import logging
import sys
import os
from dotenv import load_dotenv

from wikipedia_mcp.server import create_server

# Load environment variables from .env file if it exists
load_dotenv()


def main():
    """Run the Wikipedia MCP server."""

    class LanguageAction(argparse.Action):
        def __call__(self, parser, namespace, values, option_string=None):
            setattr(namespace, self.dest, values)
            setattr(namespace, "_language_explicitly_set", True)

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
        help=("Transport protocol for MCP communication " "(stdio for Claude Desktop, sse for HTTP streaming)"),
    )
    parser.add_argument(
        "--language",
        "-l",
        type=str,
        default="en",
        action=LanguageAction,
        help="Language code for Wikipedia (e.g., en, ja, es, zh-hans). Default: en",
    )
    parser.add_argument(
        "--country",
        "-c",
        type=str,
        help=(
            "Country/locale code for Wikipedia (e.g., US, CN, TW, Japan). "
            "Overrides --language if provided. See --list-countries for "
            "supported countries."
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
            "Access token for Wikipedia API (optional, can also be set via "
            "WIKIPEDIA_ACCESS_TOKEN environment variable)"
        ),
    )
    args = parser.parse_args()

    # Handle --list-countries
    if args.list_countries:
        from wikipedia_mcp.wikipedia_client import WikipediaClient

        client = WikipediaClient()

        print("Supported Country/Locale Codes:")
        print("=" * 40)

        # Group by language for better readability
        country_by_lang = {}
        for country, lang in client.COUNTRY_TO_LANGUAGE.items():
            if lang not in country_by_lang:
                country_by_lang[lang] = []
            country_by_lang[lang].append(country)

        # Sort languages and show examples
        for lang in sorted(country_by_lang.keys()):
            countries = country_by_lang[lang]
            # Show up to 5 country codes per language
            country_examples = countries[:5]
            if len(countries) > 5:
                country_examples.append(f"... (+{len(countries) - 5} more)")
            print(f"{lang:>6}: {', '.join(country_examples)}")

        print("\nExamples:")
        print("  wikipedia-mcp --country US    # English (United States)")
        print("  wikipedia-mcp --country CN    # Chinese Simplified (China)")
        print("  wikipedia-mcp --country TW    # Chinese Traditional (Taiwan)")
        print("  wikipedia-mcp --country Japan # Japanese")
        return

    # Validate that both --language and --country are not provided (when language is explicitly set)
    if args.country and getattr(args, "_language_explicitly_set", False):
        print("Error: Cannot specify both --language and --country. Use one or the other.")
        parser.print_help()
        return

    # Configure logging - use basicConfig for simplicity but ensure it goes to stderr
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stderr,
        force=True,  # Override any existing basicConfig
    )

    logger = logging.getLogger(__name__)

    # Get access token from argument or environment variable
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
        logger.error("Configuration error: %s", e)
        print(f"Error: {e}")
        print("\nUse --list-countries to see supported country codes.")
        return

    # Log startup information using our configured logger
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
        logger.info("To use with Claude Desktop, ensure 'wikipedia-mcp' command is in your claude_desktop_config.json.")

    if args.transport == "sse":
        logger.info("Starting SSE server on %s:%d", args.host, args.port)
        server.run(transport=args.transport, port=args.port, host=args.host)
    else:
        server.run(transport=args.transport)


if __name__ == "__main__":
    main()
