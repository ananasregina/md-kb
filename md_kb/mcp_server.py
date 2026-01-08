"""
Markdown Knowledge Base - MCP Server Module

Model Context Protocol server for AI agents and LLMs.
Provides semantic search tools for markdown collections.
"""

import logging
from typing import Any
import asyncio

from mcp.server import Server
from mcp.types import Tool, TextContent

from md_kb.database import (
    init_db,
    search_documents,
    get_document_count,
    get_all_documents,
)
from md_kb.indexer import index_directory
from md_kb.watcher import watch_directory
from md_kb.config import get_config

logger = logging.getLogger(__name__)

# Initialize the MCP server
config = get_config()
server = Server(
    name=config.get_mcp_server_name(),
    version=config.get_mcp_server_version(),
)


def _register_tools():
    """
    Register the markdown search tools with the MCP server.
    """

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        """
        List available markdown knowledge base tools.

        Returns:
            list[Tool]: The available tools
        """
        return [
            Tool(
                name="search_markdown",
                description="Search markdown documents by semantic similarity. Returns file paths with content snippets and similarity scores.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search text to find in markdown documents",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results to return (default: all)",
                        },
                        "max_distance": {
                            "type": "number",
                            "description": "Maximum similarity threshold (0.0-2.0, lower = more similar, default: 0.5)",
                        },
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="get_document_count",
                description="Get the total number of indexed markdown documents.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            ),
            Tool(
                name="list_documents",
                description="List all indexed markdown documents with pagination. Returns file paths and metadata.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of documents to return (default: all)",
                        },
                        "offset": {
                            "type": "integer",
                            "description": "Number of documents to skip for pagination (default: 0)",
                        },
                    },
                    "required": [],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        """
        Execute a markdown knowledge base tool.

        Args:
            name: Tool name (search_markdown, get_document_count, list_documents)
            arguments: Tool arguments

        Returns:
            list[TextContent]: Tool results
        """
        try:
            if name == "search_markdown":
                return await _handle_search_markdown(arguments)
            elif name == "get_document_count":
                return await _handle_get_document_count()
            elif name == "list_documents":
                return await _handle_list_documents(arguments)
            else:
                return [
                    TextContent(
                        type="text",
                        text=f"Unknown tool: {name}",
                    )
                ]

        except Exception as e:
            logger.exception(f"Error executing tool {name}")
            return [
                TextContent(
                    type="text",
                    text=f"Error: {str(e)}",
                )
            ]


async def _handle_search_markdown(arguments: dict[str, Any]) -> list[TextContent]:
    """
    Handle search_markdown tool.

    Args:
        arguments: Tool arguments (query, optional limit, optional max_distance)

    Returns:
        list[TextContent]: Matching documents with snippets
    """
    import json

    query = arguments.get("query", "")
    limit = arguments.get("limit")
    max_distance = arguments.get("max_distance", 0.5)

    if not query:
        return [TextContent(type="text", text="Error: Query is required for search")]

    documents = await search_documents(
        query=query,
        limit=limit,
        max_distance=max_distance,
    )

    # Format results with snippets
    results = []
    for doc in documents:
        # Create snippet (first 300 chars)
        snippet = doc.content[:300].replace("\n", " ")
        if len(doc.content) > 300:
            snippet += "..."

        results.append({
            "file_path": doc.file_path,
            "snippet": snippet,
            "indexed_at": doc.indexed_at,
            "updated_at": doc.updated_at,
        })

    message = (
        f"Found {len(documents)} document(s) matching '{query}':\n"
        f"{json.dumps(results, indent=2)}"
    )

    return [TextContent(type="text", text=message)]


async def _handle_get_document_count() -> list[TextContent]:
    """
    Handle get_document_count tool.

    Returns:
        list[TextContent]: Document count
    """
    count = await get_document_count()

    if count == 0:
        message = "No documents indexed yet."
    elif count == 1:
        message = "There is 1 document indexed."
    else:
        message = f"There are {count} documents indexed."

    return [TextContent(type="text", text=message)]


async def _handle_list_documents(arguments: dict[str, Any]) -> list[TextContent]:
    """
    Handle list_documents tool.

    Args:
        arguments: Tool arguments (limit, offset)

    Returns:
        list[TextContent]: List of documents
    """
    import json

    limit = arguments.get("limit")
    offset = arguments.get("offset", 0)

    documents = await get_all_documents(limit=limit, offset=offset)

    # Format results
    results = []
    for doc in documents:
        # Create snippet
        snippet = doc.content[:300].replace("\n", " ")
        if len(doc.content) > 300:
            snippet += "..."

        results.append({
            "file_path": doc.file_path,
            "snippet": snippet,
            "indexed_at": doc.indexed_at,
            "updated_at": doc.updated_at,
        })

    message = (
        f"Listing {len(documents)} document(s):\n"
        f"{json.dumps(results, indent=2)}"
    )

    return [TextContent(type="text", text=message)]


def get_server() -> Server:
    """
    Get the MCP server instance.

    Returns:
        Server: The MCP server
    """
    # Register tools
    _register_tools()

    logger.debug("MCP server ready.")

    return server


async def start_background_tasks():
    """
    Start background tasks for the MCP server.

    Runs initial index scan and starts file watcher.
    """
    logger.info("Starting background tasks...")

    # Initialize database
    await init_db()

    # Start initial index scan (non-blocking)
    async def run_initial_index():
        logger.info("Running initial index scan...")
        await index_directory()
        logger.info("Initial index scan complete.")

    # Run initial index in background
    asyncio.create_task(run_initial_index())

    # Start file watcher in background
    async def run_watcher():
        logger.info("Starting file watcher...")
        await watch_directory()

    asyncio.create_task(run_watcher())
