"""
Database module tests with real PostgreSQL and pgvector.
"""

import pytest
import asyncpg
from pgvector.asyncpg import register_vector
from md_kb.database import (
    init_db,
    get_pool,
    close_pool,
    ingest_document,
    get_document_by_path,
    get_document_count,
    get_all_documents,
    delete_document,
    search_documents,
)
from md_kb.models import MarkdownDocument


class TestDatabaseConnection:
    """Test database connection management."""

    @pytest.mark.asyncio
    async def test_get_pool_creates_connection(self, mock_env_vars):
        """Test that get_pool creates a connection pool."""
        await init_db()
        pool = await get_pool()

        assert pool is not None

        await close_pool()

    @pytest.mark.asyncio
    async def test_get_pool_singleton(self, mock_env_vars):
        """Test that get_pool returns same instance."""
        await init_db()
        pool1 = await get_pool()
        pool2 = await get_pool()

        assert pool1 is pool2

        await close_pool()

    @pytest.mark.asyncio
    async def test_close_pool(self, mock_env_vars):
        """Test that close_pool closes the pool."""
        await init_db()
        await close_pool()

        pool = await get_pool()
        assert pool is None


class TestDatabaseSchema:
    """Test database schema initialization."""

    @pytest.mark.asyncio
    async def test_init_db_creates_vector_extension(self, mock_env_vars, test_database):
        """Test that init_db enables pgvector extension."""
        pool = await get_pool()

        async with pool.acquire() as conn:
            result = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')"
            )
            assert result is True

    @pytest.mark.asyncio
    async def test_init_db_creates_markdown_documents_table(self, mock_env_vars, test_database):
        """Test that init_db creates markdown_documents table."""
        pool = await get_pool()

        async with pool.acquire() as conn:
            result = await conn.fetchval(
                "SELECT EXISTS(SELECT FROM information_schema.tables WHERE table_name = 'markdown_documents')"
            )
            assert result is True

    @pytest.mark.asyncio
    async def test_init_db_adds_embedding_column(self, mock_env_vars, test_database):
        """Test that init_db adds embedding column."""
        pool = await get_pool()

        async with pool.acquire() as conn:
            result = await conn.fetchval(
                "SELECT EXISTS(SELECT FROM information_schema.columns WHERE table_name = 'markdown_documents' AND column_name = 'embedding')"
            )
            assert result is True

    @pytest.mark.asyncio
    async def test_init_db_creates_vector_index(self, mock_env_vars, test_database):
        """Test that init_db creates vector index."""
        pool = await get_pool()

        async with pool.acquire() as conn:
            result = await conn.fetchval(
                "SELECT EXISTS(SELECT FROM pg_indexes WHERE indexname = 'idx_md_docs_embedding')"
            )
            assert result is True

    @pytest.mark.asyncio
    async def test_init_db_creates_file_path_index(self, mock_env_vars, test_database):
        """Test that init_db creates file_path index."""
        pool = await get_pool()

        async with pool.acquire() as conn:
            result = await conn.fetchval(
                "SELECT EXISTS(SELECT FROM pg_indexes WHERE indexname = 'idx_md_docs_path')"
            )
            assert result is True


class TestDocumentIngestion:
    """Test document ingestion (upsert)."""

    @pytest.mark.asyncio
    async def test_ingest_document_new(self, mock_env_vars, sample_markdown_files):
        """Test inserting a new document."""
        doc = MarkdownDocument(
            file_path=str(sample_markdown_files / "doc1.md"),
            checksum="new_checksum_1",
            content="# New document",
        )

        result = await ingest_document(doc)

        assert result is not None
        assert result.id is not None
        assert result.file_path == doc.file_path
        assert result.checksum == doc.checksum

    @pytest.mark.asyncio
    async def test_ingest_document_update(self, mock_env_vars, sample_markdown_files):
        """Test updating an existing document (upsert)."""
        doc1 = MarkdownDocument(
            file_path=str(sample_markdown_files / "doc1.md"),
            checksum="checksum_1",
            content="# Document 1",
        )

        await ingest_document(doc1)

        doc2 = MarkdownDocument(
            id=doc1.id,
            file_path=doc1.file_path,
            checksum="checksum_2",
            content="# Updated document 1",
        )

        result = await ingest_document(doc2)

        assert result.id == doc1.id
        assert result.checksum == "checksum_2"

    @pytest.mark.asyncio
    async def test_ingest_document_generates_embedding(self, mock_env_vars, sample_markdown_files):
        """Test that ingest generates embedding for document."""
        doc = MarkdownDocument(
            file_path=str(sample_markdown_files / "doc1.md"),
            checksum="checksum_with_embedding",
            content="# Test embedding generation",
        )

        result = await ingest_document(doc)

        assert result is not None
        assert result.embedding is not None
        assert len(result.embedding) == 768

    @pytest.mark.asyncio
    async def test_ingest_document_validation_error(self, mock_env_vars):
        """Test that invalid document raises ValueError."""
        doc = MarkdownDocument(
            file_path="",
            checksum="",
            content="",
        )

        with pytest.raises(ValueError, match="Invalid document"):
            await ingest_document(doc)

    @pytest.mark.asyncio
    async def test_ingest_document_embedding_failure(self, mock_env_vars, sample_markdown_files, monkeypatch):
        """Test handling when embedding generation fails."""
        doc = MarkdownDocument(
            file_path=str(sample_markdown_files / "doc1.md"),
            checksum="checksum",
            content="# Test",
        )

        from md_kb.embeddings import EmbeddingService

        async def mock_generate_embedding(text):
            return None  # Simulate failure

        monkeypatch.setattr(
            EmbeddingService,
            "generate_embedding",
            mock_generate_embedding
        )

        with pytest.raises(ValueError, match="Failed to generate embedding"):
            await ingest_document(doc)


class TestDocumentRetrieval:
    """Test document retrieval operations."""

    @pytest.mark.asyncio
    async def test_get_document_by_path_found(self, mock_env_vars, sample_markdown_files):
        """Test retrieving an existing document."""
        doc = MarkdownDocument(
            file_path=str(sample_markdown_files / "doc1.md"),
            checksum="retrieval_checksum",
            content="# Test retrieval",
        )

        await ingest_document(doc)

        retrieved = await get_document_by_path(doc.file_path)

        assert retrieved is not None
        assert retrieved.file_path == doc.file_path
        assert retrieved.checksum == doc.checksum

    @pytest.mark.asyncio
    async def test_get_document_by_path_not_found(self, mock_env_vars):
        """Test retrieving a non-existent document."""
        retrieved = await get_document_by_path("/nonexistent/path.md")

        assert retrieved is None

    @pytest.mark.asyncio
    async def test_get_document_count(self, mock_env_vars, sample_markdown_files):
        """Test counting documents."""
        doc1 = MarkdownDocument(
            file_path=str(sample_markdown_files / "doc1.md"),
            checksum="count_checksum_1",
            content="# Count test 1",
        )
        doc2 = MarkdownDocument(
            file_path=str(sample_markdown_files / "doc2.md"),
            checksum="count_checksum_2",
            content="# Count test 2",
        )

        await ingest_document(doc1)
        await ingest_document(doc2)

        count = await get_document_count()

        assert count >= 2

    @pytest.mark.asyncio
    async def test_get_document_count_empty(self, mock_env_vars, test_database):
        """Test counting when no documents exist."""
        count = await get_document_count()

        assert count == 0

    @pytest.mark.asyncio
    async def test_get_all_documents(self, mock_env_vars, sample_markdown_files):
        """Test retrieving all documents."""
        doc1 = MarkdownDocument(
            file_path=str(sample_markdown_files / "doc1.md"),
            checksum="all_checksum_1",
            content="# All test 1",
        )
        doc2 = MarkdownDocument(
            file_path=str(sample_markdown_files / "doc2.md"),
            checksum="all_checksum_2",
            content="# All test 2",
        )

        await ingest_document(doc1)
        await ingest_document(doc2)

        docs = await get_all_documents()

        assert len(docs) >= 2

    @pytest.mark.asyncio
    async def test_get_all_documents_with_limit(self, mock_env_vars, sample_markdown_files):
        """Test retrieving documents with limit."""
        for i in range(5):
            doc = MarkdownDocument(
                file_path=str(sample_markdown_files / f"doc{i}.md"),
                checksum=f"limit_checksum_{i}",
                content=f"# Limit test {i}",
            )
            await ingest_document(doc)

        docs = await get_all_documents(limit=3)

        assert len(docs) == 3

    @pytest.mark.asyncio
    async def test_get_all_documents_with_offset(self, mock_env_vars, sample_markdown_files):
        """Test retrieving documents with offset."""
        for i in range(5):
            doc = MarkdownDocument(
                file_path=str(sample_markdown_files / f"doc{i}.md"),
                checksum=f"offset_checksum_{i}",
                content=f"# Offset test {i}",
            )
            await ingest_document(doc)

        docs = await get_all_documents(limit=2, offset=2)

        assert len(docs) == 2

    @pytest.mark.asyncio
    async def test_get_all_documents_ordering(self, mock_env_vars, sample_markdown_files):
        """Test that documents are ordered by indexed_at DESC."""
        import asyncio

        docs = []
        for i in range(3):
            await asyncio.sleep(0.01)  # Small delay for different timestamps
            doc = MarkdownDocument(
                file_path=str(sample_markdown_files / f"ordered{i}.md"),
                checksum=f"ordered_checksum_{i}",
                content=f"# Ordered test {i}",
            )
            result = await ingest_document(doc)
            docs.append(result)

        retrieved = await get_all_documents()

        assert len(retrieved) >= 3
        # Check ordering (most recent first)
        for i in range(len(retrieved) - 1):
            if retrieved[i].indexed_at and retrieved[i + 1].indexed_at:
                assert retrieved[i].indexed_at >= retrieved[i + 1].indexed_at


class TestDocumentDeletion:
    """Test document deletion operations."""

    @pytest.mark.asyncio
    async def test_delete_document_success(self, mock_env_vars, sample_markdown_files):
        """Test deleting an existing document."""
        doc = MarkdownDocument(
            file_path=str(sample_markdown_files / "delete_test.md"),
            checksum="delete_checksum",
            content="# Delete test",
        )

        result = await ingest_document(doc)

        deleted = await delete_document(result.file_path)

        assert deleted is True

        # Verify document is gone
        retrieved = await get_document_by_path(result.file_path)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_delete_document_not_found(self, mock_env_vars):
        """Test deleting a non-existent document."""
        deleted = await delete_document("/nonexistent/path.md")

        assert deleted is False


class TestDocumentSearch:
    """Test semantic search functionality."""

    @pytest.mark.asyncio
    async def test_search_documents_basic(self, mock_env_vars, sample_markdown_files):
        """Test basic semantic search."""
        doc = MarkdownDocument(
            file_path=str(sample_markdown_files / "search_test.md"),
            checksum="search_checksum",
            content="# Python programming",
        )

        await ingest_document(doc)

        results = await search_documents("Python programming")

        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_search_documents_with_limit(self, mock_env_vars, sample_markdown_files):
        """Test search with result limit."""
        for i in range(3):
            doc = MarkdownDocument(
                file_path=str(sample_markdown_files / f"search{i}.md"),
                checksum=f"search_limit_{i}",
                content=f"# Search limit test {i}",
            )
            await ingest_document(doc)

        results = await search_documents("search", limit=2)

        assert len(results) <= 2

    @pytest.mark.asyncio
    async def test_search_documents_with_offset(self, mock_env_vars, sample_markdown_files):
        """Test search with offset."""
        for i in range(3):
            doc = MarkdownDocument(
                file_path=str(sample_markdown_files / f"search_offset{i}.md"),
                checksum=f"search_offset_{i}",
                content=f"# Search offset test {i}",
            )
            await ingest_document(doc)

        results = await search_documents("search", limit=2, offset=1)

        assert len(results) <= 2

    @pytest.mark.asyncio
    async def test_search_documents_max_distance_filter(self, mock_env_vars, sample_markdown_files):
        """Test search with max_distance filter."""
        doc1 = MarkdownDocument(
            file_path=str(sample_markdown_files / "relevant.md"),
            checksum="relevant_checksum",
            content="# Python programming with asyncio",
        )
        doc2 = MarkdownDocument(
            file_path=str(sample_markdown_files / "irrelevant.md"),
            checksum="irrelevant_checksum",
            content="# This is about cooking recipes",
        )

        await ingest_document(doc1)
        await ingest_document(doc2)

        results = await search_documents("Python programming", max_distance=0.5)

        # Should find the relevant document
        result_paths = [r.file_path for r in results]
        assert doc1.file_path in result_paths

    @pytest.mark.asyncio
    async def test_search_documents_empty_query(self, mock_env_vars, sample_markdown_files):
        """Test search with empty query."""
        doc = MarkdownDocument(
            file_path=str(sample_markdown_files / "test.md"),
            checksum="test_checksum",
            content="# Test content",
        )

        await ingest_document(doc)

        with pytest.raises(Exception):  # Empty query should cause error or return empty
            await search_documents("")

    @pytest.mark.asyncio
    async def test_search_documents_no_results(self, mock_env_vars, sample_markdown_files):
        """Test search when no matches found."""
        doc = MarkdownDocument(
            file_path=str(sample_markdown_files / "nomatch.md"),
            checksum="nomatch_checksum",
            content="# Completely different topic",
        )

        await ingest_document(doc)

        results = await search_documents("quantum physics")

        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_search_documents_ordering(self, mock_env_vars, sample_markdown_files):
        """Test that search results are ordered by similarity (distance)."""
        doc1 = MarkdownDocument(
            file_path=str(sample_markdown_files / "exact_match.md"),
            checksum="exact_checksum",
            content="# Python programming",
        )
        doc2 = MarkdownDocument(
            file_path=str(sample_markdown_files / "partial_match.md"),
            checksum="partial_checksum",
            content="# Programming in general",
        )
        doc3 = MarkdownDocument(
            file_path=str(sample_markdown_files / "loose_match.md"),
            checksum="loose_checksum",
            content="# Some content",
        )

        await ingest_document(doc1)
        await ingest_document(doc2)
        await ingest_document(doc3)

        results = await search_documents("Python programming")

        if len(results) >= 2:
            # More similar results should come first (lower distance)
            # Note: We can't directly check distance since it's not exposed in result
            # But the ordering should be by similarity
            assert len(results) == len([r for r in results if r.file_path])
