"""
MCP server module tests.
"""

import pytest
from mcp.types import Tool
from md_kb.mcp_server import (
    _handle_create_document,
    _handle_update_document,
    _handle_delete_document,
    _handle_list_files,
    get_server,
)
from md_kb.indexer import delete_file


class TestMCPServerTools:
    """Test MCP server tool definitions."""

    def test_server_initialization(self):
        """Test that MCP server initializes with all tools."""
        server = get_server()
        assert server is not None


class TestMCPCreateDocument:
    """Test create_document MCP tool."""

    @pytest.mark.asyncio
    async def test_create_document_success(self, mock_env_vars):
        """Test creating a document via MCP tool."""
        arguments = {
            "filename": "mcp_test_create.md",
            "content": "# MCP Test\n\nCreated via MCP tool."
        }

        result = await _handle_create_document(arguments)

        assert len(result) == 1
        assert "Created document" in result[0].text
        assert "mcp_test_create.md" in result[0].text

        # Clean up
        await delete_file("mcp_test_create.md")

    @pytest.mark.asyncio
    async def test_create_document_missing_filename(self, mock_env_vars):
        """Test error when filename is missing."""
        arguments = {"content": "# Test"}

        result = await _handle_create_document(arguments)

        assert len(result) == 1
        assert "Error: filename is required" in result[0].text

    @pytest.mark.asyncio
    async def test_create_document_missing_content(self, mock_env_vars):
        """Test error when content is missing."""
        arguments = {"filename": "test.md"}

        result = await _handle_create_document(arguments)

        assert len(result) == 1
        assert "Error: content is required" in result[0].text


class TestMCPUpdateDocument:
    """Test update_document MCP tool."""

    @pytest.mark.asyncio
    async def test_update_document_success(self, mock_env_vars):
        """Test updating a document via MCP tool."""
        from md_kb.indexer import create_file

        # Create file first
        filename = "mcp_test_update.md"
        await create_file(filename, "# Original")

        # Update via MCP
        arguments = {
            "filename": filename,
            "content": "# Updated\n\nNew content."
        }

        result = await _handle_update_document(arguments)

        assert len(result) == 1
        assert "Updated document" in result[0].text
        assert filename in result[0].text

        # Clean up
        await delete_file(filename)

    @pytest.mark.asyncio
    async def test_update_document_missing_filename(self, mock_env_vars):
        """Test error when filename is missing."""
        arguments = {"content": "# Test"}

        result = await _handle_update_document(arguments)

        assert len(result) == 1
        assert "Error: filename is required" in result[0].text

    @pytest.mark.asyncio
    async def test_update_document_missing_content(self, mock_env_vars):
        """Test error when content is missing."""
        arguments = {"filename": "test.md"}

        result = await _handle_update_document(arguments)

        assert len(result) == 1
        assert "Error: content is required" in result[0].text


class TestMCPDeleteDocument:
    """Test delete_document MCP tool."""

    @pytest.mark.asyncio
    async def test_delete_document_success(self, mock_env_vars):
        """Test deleting a document via MCP tool."""
        from md_kb.indexer import create_file

        # Create file first
        filename = "mcp_test_delete.md"
        await create_file(filename, "# To delete")

        # Delete via MCP
        arguments = {"filename": filename}

        result = await _handle_delete_document(arguments)

        assert len(result) == 1
        assert "Deleted document" in result[0].text
        assert filename in result[0].text

    @pytest.mark.asyncio
    async def test_delete_document_not_found(self, mock_env_vars):
        """Test deleting a non-existent document."""
        arguments = {"filename": "nonexistent.md"}

        result = await _handle_delete_document(arguments)

        assert len(result) == 1
        assert "Document not found" in result[0].text

    @pytest.mark.asyncio
    async def test_delete_document_missing_filename(self, mock_env_vars):
        """Test error when filename is missing."""
        arguments = {}

        result = await _handle_delete_document(arguments)

        assert len(result) == 1
        assert "Error: filename is required" in result[0].text


class TestMCPListFiles:
    """Test list_files MCP tool."""

    @pytest.mark.asyncio
    async def test_list_files_success(self, mock_env_vars):
        """Test listing files via MCP tool."""
        from md_kb.indexer import create_file

        # Create test files
        await create_file("mcp_list_1.md", "# File 1")
        await create_file("mcp_list_2.md", "# File 2")

        result = await _handle_list_files()

        assert len(result) == 1
        assert "Found" in result[0].text or "documents" in result[0].text.lower()
        assert "mcp_list_1.md" in result[0].text
        assert "mcp_list_2.md" in result[0].text

        # Clean up
        await delete_file("mcp_list_1.md")
        await delete_file("mcp_list_2.md")
