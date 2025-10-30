#!/usr/bin/env python3
"""Main entry point for YouTube Crawler MCP Server

Supports multiple transport modes:
- stdio: For local Claude Desktop usage
- streamable-http: For remote access via Claude API, Lambda, etc.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.dirname(__file__))

from src.fastmcp_server import mcp

if __name__ == "__main__":
    # Get transport mode from environment or command line
    transport = os.getenv("MCP_TRANSPORT", "stdio")

    if len(sys.argv) > 1:
        transport = sys.argv[1]

    print(f"Starting YouTube Crawler MCP Server with {transport} transport...", file=sys.stderr)

    # Run server with specified transport
    mcp.run(transport=transport)
