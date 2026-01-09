"""
Markdown Knowledge Base - Main Entry Point

The markdown knowledge base has multiple access methods:
- CLI: One-shot search commands
- MCP: Server for AI agents with continuous file watching
"""

import sys
import asyncio
import logging
from logging.handlers import RotatingFileHandler
from typing import NoReturn

from md_kb.cli import app as cli_app
from md_kb.mcp_server import get_server, start_background_tasks
from md_kb.jsonrpc_server import get_app as get_jsonrpc_app
from md_kb.config import get_config

logger = logging.getLogger(__name__)

config = get_config()


def setup_logging() -> None:
    """
    Set up file and console logging with rotation.

    Creates both file and console handlers with different log levels.
    File logs include timestamps and caller info.
    """
    log_file = config.get_log_file()
    log_level_file = config.get_log_level()
    log_level_console = config.get_log_level_console()
    max_bytes = config.get_log_max_bytes()
    backup_count = config.get_log_backup_count()

    # Ensure config directory exists
    log_file.parent.mkdir(parents=True, exist_ok=True)

    # Get root logger
    root_logger = logging.getLogger()

    # Set root log level to the most verbose of the two handlers
    root_logger.setLevel(min(
        getattr(logging, log_level_file.upper()),
        getattr(logging, log_level_console.upper()),
    ))

    # Remove any existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # File handler with rotation - includes timestamps and caller info
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
    )
    file_handler.setLevel(getattr(logging, log_level_file.upper()))
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)

    # Console handler - simpler format, higher threshold
    console_formatter = logging.Formatter("%(levelname)s: %(message)s")
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level_console.upper()))
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)


def main() -> None:
    """
    Main entry point for the markdown knowledge base.

    Dispatches to:
    - CLI mode (default) - One-shot search with forced refresh
    - MCP server mode (--mcp flag) - Long-lived with file watching over stdio
    - JSON-RPC server mode (--jsonrpc flag) - Long-lived with file watching over HTTP
    """
    # Check for --mcp flag (must be before Typer parsing)
    if "--mcp" in sys.argv or "-m" in sys.argv:
        asyncio.run(_run_mcp_server())
    elif "--jsonrpc" in sys.argv or "-j" in sys.argv:
        _run_jsonrpc_server()
    else:
        # CLI mode
        try:
            cli_app()
        except SystemExit:
            # Typer calls sys.exit, which is normal
            pass


async def _run_mcp_server() -> None:
    """
    Run MCP server.

    The markdown knowledge base communicates with AI through this channel.
    Runs initial index scan and starts file watcher in background.
    """
    import mcp.server.stdio

    # Set up logging for MCP server
    setup_logging()

    # Start background tasks (initial index + watcher) in the same event loop
    await start_background_tasks()

    # Get the MCP server
    server = get_server()

    # Run the server
    logger.info("Starting markdown knowledge base MCP server...")

    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def _run_jsonrpc_server() -> None:
    """
    Run JSON-RPC server.

    Exposes an HTTP-based JSON-RPC 2.0 API for remote semantic search.
    Runs initial index scan and starts file watcher in background.

    WARNING: This server is designed for local use only. It has no authentication
    or rate limiting. Do not expose it to the internet without proper security measures.
    """
    import uvicorn

    # Set up logging for JSON-RPC server
    setup_logging()

    # Get the JSON-RPC app
    app = get_jsonrpc_app()

    # Get configuration
    host = config.get_jsonrpc_host()
    port = config.get_jsonrpc_port()

    logger.info(f"Starting markdown knowledge base JSON-RPC server on http://{host}:{port}/")
    logger.warning("Here be dragons: This server has no authentication. Do not expose to the internet.")

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
