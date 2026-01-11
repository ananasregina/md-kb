"""
Markdown Knowledge Base - JSON-RPC Server Module

HTTP-based JSON-RPC 2.0 server for remote semantic search.
"""

import logging
from typing import Any
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

from md_kb.database import (
    init_db,
    search_documents,
    get_document_count,
    get_all_documents,
)
from md_kb.indexer import index_directory, create_file, update_file, delete_file, list_files
from md_kb.watcher import watch_directory
from md_kb.config import get_config

logger = logging.getLogger(__name__)

config = get_config()
app = FastAPI(title=config.get_mcp_server_name(), version=config.get_mcp_server_version())


class JSONRPCError(Exception):
    """JSON-RPC 2.0 error"""

    def __init__(self, code: int, message: str, data: Any = None):
        self.code = code
        self.message = message
        self.data = data


def jsonrpc_error_response(id: Any, code: int, message: str, data: Any = None) -> dict:
    """Create a JSON-RPC 2.0 error response"""
    error = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return {"jsonrpc": "2.0", "error": error, "id": id}


def jsonrpc_success_response(id: Any, result: Any) -> dict:
    """Create a JSON-RPC 2.0 success response"""
    return {"jsonrpc": "2.0", "result": result, "id": id}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for the FastAPI app.
    
    Starts background tasks on startup and performs cleanup on shutdown.
    """
    logger.info("Starting markdown knowledge base JSON-RPC server...")

    try:
        await init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise JSONRPCError(-32603, "Internal error", f"Database initialization failed: {str(e)}")

    async def run_initial_index():
        logger.info("Running initial index scan...")
        try:
            stats = await index_directory()
            logger.info(
                f"Initial index scan complete: {stats['indexed']} new, "
                f"{stats['updated']} updated, {stats['deleted']} deleted, "
                f"{stats['skipped']} skipped"
            )
        except Exception as e:
            logger.error(f"Initial index scan failed: {e}")

    async def run_watcher():
        logger.info("Starting file watcher...")
        try:
            await watch_directory()
        except Exception as e:
            logger.error(f"File watcher failed: {e}")

    asyncio.create_task(run_initial_index())
    asyncio.create_task(run_watcher())

    yield

    logger.info("Shutting down markdown knowledge base JSON-RPC server...")


app.router.lifespan_context = lifespan


@app.post("/")
async def jsonrpc_handler(request: Request):
    """
    Handle JSON-RPC 2.0 requests.
    
    Supports:
    - search(query, limit?, max_distance?): Search documents by semantic similarity
    - get_document_count(): Get total number of indexed documents
    - list_documents(limit?, offset?): List all documents with pagination
    """
    try:
        request_body = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")

    jsonrpc_version = request_body.get("jsonrpc")
    method = request_body.get("method")
    params = request_body.get("params", {})
    request_id = request_body.get("id")

    if jsonrpc_version != "2.0":
        return JSONResponse(
            content=jsonrpc_error_response(request_id, -32600, "Invalid Request", "jsonrpc version must be '2.0'"),
            status_code=400
        )

    if not method:
        return JSONResponse(
            content=jsonrpc_error_response(request_id, -32600, "Invalid Request", "method is required"),
            status_code=400
        )

    try:
        if method == "search":
            return await _handle_search(params, request_id)
        elif method == "get_document_count":
            return await _handle_get_document_count(request_id)
        elif method == "list_documents":
            return await _handle_list_documents(params, request_id)
        elif method == "create_document":
            return await _handle_create_document(params, request_id)
        elif method == "update_document":
            return await _handle_update_document(params, request_id)
        elif method == "delete_document":
            return await _handle_delete_document(params, request_id)
        elif method == "list_files":
            return await _handle_list_files(request_id)
        else:
            return JSONResponse(
                content=jsonrpc_error_response(request_id, -32601, "Method not found", f"Method '{method}' not found"),
                status_code=404
            )
    except JSONRPCError as e:
        return JSONResponse(
            content=jsonrpc_error_response(request_id, e.code, e.message, e.data),
            status_code=500 if e.code == -32603 else 400
        )
    except Exception as e:
        logger.exception(f"Error processing request: {e}")
        return JSONResponse(
            content=jsonrpc_error_response(request_id, -32603, "Internal error", str(e)),
            status_code=500
        )


async def _handle_search(params: dict, request_id: Any) -> JSONResponse:
    """Handle search method"""
    query = params.get("query")
    limit = params.get("limit")
    max_distance = params.get("max_distance", 0.5)

    if not query or not isinstance(query, str):
        raise JSONRPCError(-32602, "Invalid params", "'query' parameter is required and must be a string")

    if max_distance is not None and (not isinstance(max_distance, (int, float)) or max_distance < 0 or max_distance > 2):
        raise JSONRPCError(-32602, "Invalid params", "'max_distance' must be a number between 0 and 2")

    if limit is not None and (not isinstance(limit, int) or limit < 1):
        raise JSONRPCError(-32602, "Invalid params", "'limit' must be a positive integer")

    try:
        documents = await search_documents(
            query=query,
            limit=limit,
            max_distance=max_distance,
        )
    except Exception as e:
        raise JSONRPCError(-32603, "Internal error", f"Search failed: {str(e)}")

    results = []
    for doc in documents:
        result = {
            "file_path": doc.file_path,
            "content": doc.content,
            "distance": doc.distance,
            "indexed_at": doc.indexed_at,
            "updated_at": doc.updated_at,
        }
        results.append(result)

    return JSONResponse(content=jsonrpc_success_response(request_id, results))


async def _handle_get_document_count(request_id: Any) -> JSONResponse:
    """Handle get_document_count method"""
    try:
        count = await get_document_count()
    except Exception as e:
        raise JSONRPCError(-32603, "Internal error", f"Failed to get document count: {str(e)}")

    return JSONResponse(content=jsonrpc_success_response(request_id, count))


async def _handle_list_documents(params: dict, request_id: Any) -> JSONResponse:
    """Handle list_documents method"""
    limit = params.get("limit")
    offset = params.get("offset", 0)

    if limit is not None and (not isinstance(limit, int) or limit < 1):
        raise JSONRPCError(-32602, "Invalid params", "'limit' must be a positive integer")

    if offset is not None and (not isinstance(offset, int) or offset < 0):
        raise JSONRPCError(-32602, "Invalid params", "'offset' must be a non-negative integer")

    try:
        documents = await get_all_documents(limit=limit, offset=offset)
    except Exception as e:
        raise JSONRPCError(-32603, "Internal error", f"Failed to list documents: {str(e)}")

    results = []
    for doc in documents:
        result = {
            "file_path": doc.file_path,
            "content": doc.content,
            "indexed_at": doc.indexed_at,
            "updated_at": doc.updated_at,
        }
        results.append(result)

    return JSONResponse(content=jsonrpc_success_response(request_id, results))


async def _handle_create_document(params: dict, request_id: Any) -> JSONResponse:
    """Handle create_document method"""
    filename = params.get("filename")
    content = params.get("content")

    if not filename or not isinstance(filename, str):
        raise JSONRPCError(-32602, "Invalid params", "'filename' parameter is required and must be a string")

    if not content or not isinstance(content, str):
        raise JSONRPCError(-32602, "Invalid params", "'content' parameter is required and must be a string")

    if not filename.lower().endswith(".md"):
        raise JSONRPCError(-32602, "Invalid params", "'filename' must end with .md")

    try:
        doc = await create_file(filename, content)
    except ValueError as e:
        raise JSONRPCError(-32602, "Invalid params", str(e))
    except Exception as e:
        raise JSONRPCError(-32603, "Internal error", f"Create document failed: {str(e)}")

    result = {
        "file_path": doc.file_path,
        "indexed_at": doc.indexed_at,
        "updated_at": doc.updated_at,
    }

    return JSONResponse(content=jsonrpc_success_response(request_id, result))


async def _handle_update_document(params: dict, request_id: Any) -> JSONResponse:
    """Handle update_document method"""
    filename = params.get("filename")
    content = params.get("content")

    if not filename or not isinstance(filename, str):
        raise JSONRPCError(-32602, "Invalid params", "'filename' parameter is required and must be a string")

    if not content or not isinstance(content, str):
        raise JSONRPCError(-32602, "Invalid params", "'content' parameter is required and must be a string")

    if not filename.lower().endswith(".md"):
        raise JSONRPCError(-32602, "Invalid params", "'filename' must end with .md")

    try:
        doc = await update_file(filename, content)
    except ValueError as e:
        raise JSONRPCError(-32602, "Invalid params", str(e))
    except Exception as e:
        raise JSONRPCError(-32603, "Internal error", f"Update document failed: {str(e)}")

    result = {
        "file_path": doc.file_path,
        "indexed_at": doc.indexed_at,
        "updated_at": doc.updated_at,
    }

    return JSONResponse(content=jsonrpc_success_response(request_id, result))


async def _handle_delete_document(params: dict, request_id: Any) -> JSONResponse:
    """Handle delete_document method"""
    filename = params.get("filename")

    if not filename or not isinstance(filename, str):
        raise JSONRPCError(-32602, "Invalid params", "'filename' parameter is required and must be a string")

    if not filename.lower().endswith(".md"):
        raise JSONRPCError(-32602, "Invalid params", "'filename' must end with .md")

    try:
        deleted = await delete_file(filename)
    except ValueError as e:
        raise JSONRPCError(-32602, "Invalid params", str(e))
    except Exception as e:
        raise JSONRPCError(-32603, "Internal error", f"Delete document failed: {str(e)}")

    if not deleted:
        raise JSONRPCError(-32602, "Invalid params", f"Document not found: {filename}")

    result = {"deleted": True, "filename": filename}

    return JSONResponse(content=jsonrpc_success_response(request_id, result))


async def _handle_list_files(request_id: Any) -> JSONResponse:
    """Handle list_files method"""
    try:
        filenames = await list_files()
    except Exception as e:
        raise JSONRPCError(-32603, "Internal error", f"List files failed: {str(e)}")

    result = {"files": filenames, "count": len(filenames)}

    return JSONResponse(content=jsonrpc_success_response(request_id, result))


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "md-kb JSON-RPC server"}


def get_app() -> FastAPI:
    """
    Get the FastAPI application instance.

    Returns:
        FastAPI: The FastAPI app
    """
    logger.debug("JSON-RPC server ready.")
    return app
