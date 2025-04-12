"""
Main entry point for the Wikipedia MCP server.
"""

import argparse
import logging
import os
from dotenv import load_dotenv

from wikipedia_mcp.server import create_server

# Load environment variables from .env file if it exists
load_dotenv()

def main():
    """Run the Wikipedia MCP server."""
    parser = argparse.ArgumentParser(description="Wikipedia MCP Server")
    parser.add_argument(
        "--log-level", 
        type=str, 
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level"
    )
    parser.add_argument(
        "--transport",
        type=str,
        default="stdio",
        choices=["stdio", "sse"],
        help="Transport protocol for MCP communication (stdio for Claude Desktop, sse for HTTP streaming)"
    )
    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Create and start the server
    server = create_server()
    
    # Note: MCP doesn't use traditional HTTP ports. It communicates through stdio or SSE.
    print(f"Starting Wikipedia MCP server with {args.transport} transport")
    print(f"To use with Claude Desktop, configure claude_desktop_config.json with:")
    print(f"""
    {{
      "mcpServers": {{
        "wikipedia": {{
          "command": "wikipedia-mcp"
        }}
      }}
    }}
    """)
    
    server.run(transport=args.transport)

if __name__ == "__main__":
    main() 