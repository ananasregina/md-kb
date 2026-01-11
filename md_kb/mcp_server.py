"""
Markdown Knowledge Base - MCP Server Module

Model Context Protocol server for AI agents and LLMs.
Provides semantic search tools for markdown collections.
"""

import asyncio
import logging
from typing import Any

from mcp.server import Server
from mcp.types import TextContent, Tool

from md_kb.config import get_config
from md_kb.database import (
    get_all_documents,
    get_document_count,
    init_db,
    search_documents,
)
from md_kb.indexer import index_directory, create_file, update_file, delete_file, list_files
from md_kb.watcher import watch_directory

logger = logging.getLogger(__name__)

# Initialize the MCP server
config = get_config()
server = Server(
    name=config.get_mcp_server_name(),
    version=config.get_mcp_server_version(),
)

# Get database name for tool naming
database_name = config.get_database_name()

# Generate dynamic tool names based on database name
if database_name:
    search_tool_name = f"search_markdown_{database_name}"
    count_tool_name = f"get_document_count_{database_name}"
    list_tool_name = f"list_documents_{database_name}"
    create_tool_name = f"create_document_{database_name}"
    update_tool_name = f"update_document_{database_name}"
    delete_tool_name = f"delete_document_{database_name}"
    list_files_tool_name = f"list_files_{database_name}"
    db_context = f" in '{database_name}' knowledge base"
else:
    search_tool_name = "search_markdown"
    count_tool_name = "get_document_count"
    list_tool_name = "list_documents"
    create_tool_name = "create_document"
    update_tool_name = "update_document"
    delete_tool_name = "delete_document"
    list_files_tool_name = "list_files"
    db_context = ""


@server.list_tools()
async def list_tools() -> list[Tool]:
    """
    List available markdown knowledge base tools.

    Returns:
        list[Tool]: The available tools
    """
    return [
            Tool(
                name=search_tool_name,
                description=(
                    f"Search markdown documents{db_context} by semantic similarity. "
                    "Returns file paths with content snippets and similarity scores."
                ),
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
                            "description": (
                                "Maximum similarity threshold (0.0-2.0, "
                                "lower = more similar, default: 0.5)"
                            ),
                        },
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name=count_tool_name,
                description=f"Get the total number of indexed markdown documents{db_context}.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            ),
            Tool(
                name=list_tool_name,
                description=(
                    f"List all indexed markdown documents{db_context} with pagination. "
                    "Returns file paths and metadata."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of documents to return (default: all)",
                        },
                        "offset": {
                            "type": "integer",
                            "description": (
                            "Number of documents to skip for pagination (default: 0)"
                            ),
                        },
                    },
                    "required": [],
                },
            ),
            Tool(
                name=create_tool_name,
                description=(
                    f"Create a new markdown document{db_context}. "
                    "Writes to disk and updates the database."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "filename": {
                            "type": "string",
                            "description": "Name of the file (must end with .md)",
                        },
                        "content": {
                            "type": "string",
                            "description": "Markdown content to write",
                        },
                    },
                    "required": ["filename", "content"],
                },
            ),
            Tool(
                name=update_tool_name,
                description=(
                    f"Update an existing markdown document{db_context}. "
                    "Writes to disk and updates the database."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "filename": {
                            "type": "string",
                            "description": "Name of the file (must end with .md)",
                        },
                        "content": {
                            "type": "string",
                            "description": "New markdown content",
                        },
                    },
                    "required": ["filename", "content"],
                },
            ),
            Tool(
                name=delete_tool_name,
                description=(
                    f"Delete a markdown document{db_context}. "
                    "Removes from disk and database."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "filename": {
                            "type": "string",
                            "description": "Name of the file (must end with .md)",
                        },
                    },
                    "required": ["filename"],
                },
            ),
            Tool(
                name=list_files_tool_name,
                description=(
                    f"List all markdown filenames{db_context} without full paths."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            ),
        ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """
    Execute a markdown knowledge base tool.

    Args:
        name: Tool name
        arguments: Tool arguments

    Returns:
        list[TextContent]: Tool results
    """
    logger.debug(f"call_tool called with name={name}, search_tool_name={search_tool_name}, create_tool_name={create_tool_name}")

    try:
        if name == search_tool_name:
            logger.debug(f"Routing to search handler: {search_tool_name}")
            return await _handle_search_markdown(arguments)
        elif name == count_tool_name:
            logger.debug(f"Routing to count handler: {count_tool_name}")
            return await _handle_get_document_count()
        elif name == list_tool_name:
            logger.debug(f"Routing to list documents handler: {list_tool_name}")
            return await _handle_list_documents(arguments)
        elif name == create_tool_name:
            logger.debug(f"Routing to create document handler: {create_tool_name}")
            return await _handle_create_document(arguments)
        elif name == update_tool_name:
            logger.debug(f"Routing to update document handler: {update_tool_name}")
            return await _handle_update_document(arguments)
        elif name == delete_tool_name:
            logger.debug(f"Routing to delete document handler: {delete_tool_name}")
            return await _handle_delete_document(arguments)
        elif name == list_files_tool_name:
            logger.debug(f"Routing to list files handler: {list_files_tool_name}")
            return await _handle_list_files()
        else:
            logger.warning(f"Unknown tool requested: {name}")
            logger.debug(f"Available tool names: {search_tool_name}, {count_tool_name}, {list_tool_name}, {create_tool_name}, {update_tool_name}, {delete_tool_name}, {list_files_tool_name}")
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
        # Create snippet (first 600 chars)
        snippet = doc.content[:600].replace("\n", " ")
        if len(doc.content) > 600:
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
        snippet = doc.content[:600].replace("\n", " ")
        if len(doc.content) > 600:
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


async def _handle_create_document(arguments: dict[str, Any]) -> list[TextContent]:
    """
    Handle create_document tool.

    Args:
        arguments: Tool arguments (filename, content)

    Returns:
        list[TextContent]: Created document info
    """
    import json

    filename = arguments.get("filename", "")
    content = arguments.get("content", "")

    if not filename:
        return [TextContent(type="text", text="Error: filename is required")]

    if not content:
        return [TextContent(type="text", text="Error: content is required")]

    doc = await create_file(filename, content)

    result = {
        "file_path": doc.file_path,
        "indexed_at": doc.indexed_at,
        "updated_at": doc.updated_at,
    }

    message = (
        f"Created document: {filename}\n"
        f"{json.dumps(result, indent=2)}"
    )

    return [TextContent(type="text", text=message)]


async def _handle_update_document(arguments: dict[str, Any]) -> list[TextContent]:
    """
    Handle update_document tool.

    Args:
        arguments: Tool arguments (filename, content)

    Returns:
        list[TextContent]: Updated document info
    """
    import json

    filename = arguments.get("filename", "")
    content = arguments.get("content", "")

    if not filename:
        return [TextContent(type="text", text="Error: filename is required")]

    if not content:
        return [TextContent(type="text", text="Error: content is required")]

    doc = await update_file(filename, content)

    result = {
        "file_path": doc.file_path,
        "indexed_at": doc.indexed_at,
        "updated_at": doc.updated_at,
    }

    message = (
        f"Updated document: {filename}\n"
        f"{json.dumps(result, indent=2)}"
    )

    return [TextContent(type="text", text=message)]


async def _handle_delete_document(arguments: dict[str, Any]) -> list[TextContent]:
    """
    Handle delete_document tool.

    Args:
        arguments: Tool arguments (filename)

    Returns:
        list[TextContent]: Deletion result
    """
    filename = arguments.get("filename", "")

    if not filename:
        return [TextContent(type="text", text="Error: filename is required")]

    deleted = await delete_file(filename)

    message = f"Deleted document: {filename}" if deleted else f"Document not found: {filename}"

    return [TextContent(type="text", text=message)]


async def _handle_list_files() -> list[TextContent]:
    """
    Handle list_files tool.

    Returns:
        list[TextContent]: List of filenames
    """
    import json

    filenames = await list_files()

    if not filenames:
        message = "No documents found."
    elif len(filenames) == 1:
        message = f"Found 1 document:\n{json.dumps(filenames, indent=2)}"
    else:
        message = f"Found {len(filenames)} documents:\n{json.dumps(filenames, indent=2)}"

    return [TextContent(type="text", text=message)]


def get_server() -> Server:
    """
    Get the MCP server instance.

    Returns:
        Server: The MCP server
    """
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
