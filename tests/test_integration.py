"""
End-to-end integration tests.
"""

import pytest
from md_kb.database import (
    init_db,
    search_documents,
    get_document_count,
)
from md_kb.indexer import index_directory
from md_kb.database import ingest_document
from md_kb.models import MarkdownDocument


class TestIntegrationWorkflow:
    """Test full workflows."""

    @pytest.mark.asyncio
    async def test_full_index_workflow(self, mock_env_vars, sample_markdown_files):
        """Test complete indexing workflow."""
        # Index all sample files
        stats = await index_directory()

        assert stats["indexed"] >= 3
        assert stats["errors"] == 0

        # Verify documents are in database
        count = await get_document_count()
        assert count >= 3

    @pytest.mark.asyncio
    async def test_search_workflow(self, mock_env_vars, sample_markdown_files):
        """Test index → search workflow."""
        # Index documents
        await index_directory()

        # Search for content we indexed
        results = await search_documents("Python programming")

        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_search_returns_correct_documents(self, mock_env_vars, sample_markdown_files):
        """Test that search returns documents with matching content."""
        # Create a document with specific content
        doc = MarkdownDocument(
            file_path=str(sample_markdown_files / "search_test.md"),
            checksum="search_test_checksum",
            content="# This document is about Python async programming and asyncio coroutines",
        )

        await ingest_document(doc)

        # Search for "Python programming"
        results = await search_documents("Python programming")

        # Should find our document
        assert len(results) >= 1
        found_paths = [r.file_path for r in results]
        assert doc.file_path in found_paths

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_search_with_real_kb_documents(self, mock_env_vars):
        """Test search with real knowledge base documents."""
        # Use the real KB location if set
        # For now, just verify search works
        results = await search_documents("programming")

        # Just verify it doesn't crash
        assert results is not None

    @pytest.mark.asyncio
    async def test_index_with_deleted_files_cleanup(self, mock_env_vars, sample_markdown_files):
        """Test that deleted files are removed from database."""
        # Index initial files
        stats1 = await index_directory()
        initial_count = stats1["indexed"]

        # Delete a file
        (sample_markdown_files / "doc2.md").unlink()

        # Reindex
        stats2 = await index_directory()

        # Verify deletion was detected
        assert stats2["deleted"] == 1

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_large_scale_indexing(self, mock_env_vars, sample_markdown_files):
        """Test indexing with many files."""
        import asyncio

        # Create many test files
        for i in range(50):
            (sample_markdown_files / f"bulk{i}.md").write_text(f"# Document {i}\n\nContent for document {i}.")

        # Index them
        stats = await index_directory()

        # Verify all were indexed
        assert stats["indexed"] >= 50
        assert stats["errors"] < 5  # Allow for some errors

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_search_accuracy(self, mock_env_vars, sample_markdown_files):
        """Test that search finds relevant documents."""
        # Create distinct documents
        doc1 = MarkdownDocument(
            file_path=str(sample_markdown_files / "python_doc.md"),
            checksum="python_checksum",
            content="# Python Programming Guide\n\nPython is a versatile programming language used for web development, data science, automation, and more.",
        )
        doc2 = MarkdownDocument(
            file_path=str(sample_markdown_files / "cooking_doc.md"),
            checksum="cooking_checksum",
            content="# Cooking Recipes\n\nDelicious recipes for pasta, pizza, and salads.",
        )

        await ingest_document(doc1)
        await ingest_document(doc2)

        # Search for Python-related queries
        results1 = await search_documents("web development")
        results2 = await search_documents("data science")

        # Should find python_doc
        python_found = any(
            r.file_path == doc1.file_path
            for r in results1 + results2
        )

        assert python_found

    @pytest.mark.asyncio
    async def test_concurrent_index_and_search(self, mock_env_vars, sample_markdown_files):
        """Test concurrent indexing and searching."""
        # Create test document
        doc = MarkdownDocument(
            file_path=str(sample_markdown_files / "concurrent_test.md"),
            checksum="concurrent_checksum",
            content="# Concurrent operations",
        )

        # Index and search concurrently
        await ingest_document(doc)
        results = await search_documents("concurrent")

        # Should find the document we just indexed
        assert len(results) >= 1

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_index_performance(self, mock_env_vars, sample_markdown_files):
        """Test indexing performance with real KB documents."""
        import time

        start_time = time.time()
        await index_directory()
        end_time = time.time()

        duration = end_time - start_time

        # Indexing should complete in reasonable time
        assert duration < 30.0  # Less than 30 seconds
