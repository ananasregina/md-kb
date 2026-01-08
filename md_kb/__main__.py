"""
Markdown Knowledge Base - Main Entry Point

The markdown knowledge base has multiple access methods:
- CLI: One-shot search commands
- MCP: Server for AI agents with continuous file watching
"""

import sys
import asyncio
import logging
from typing import NoReturn

from md_kb.cli import app as cli_app
from md_kb.mcp_server import get_server, start_background_tasks

logger = logging.getLogger(__name__)


def main() -> NoReturn:
    """
    Main entry point for the markdown knowledge base.

    Dispatches to:
    - CLI mode (default) - One-shot search with forced refresh
    - MCP server mode (--mcp flag) - Long-lived with file watching
    """
    # Check for --mcp flag (must be before Typer parsing)
    if "--mcp" in sys.argv or "-m" in sys.argv:
        _run_mcp_server()
    else:
        # CLI mode
        try:
            cli_app()
        except SystemExit:
            # Typer calls sys.exit, which is normal
            pass


def _run_mcp_server() -> NoReturn:
    """
    Run MCP server.

    The markdown knowledge base communicates with AI through this channel.
    Runs initial index scan and starts file watcher in background.
    """
    import mcp.server.stdio

    # Start background tasks (initial index + watcher)
    asyncio.run(start_background_tasks())

    # Get the MCP server
    server = get_server()

    # Run the server
    logger.info("Starting markdown knowledge base MCP server...")

    # Run stdio server (async)
    async def run_server():
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options(),
            )

    asyncio.run(run_server())

    # Should never reach here
    sys.exit(0)


if __name__ == "__main__":
    main()
