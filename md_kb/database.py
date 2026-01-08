"""
Markdown Knowledge Base - Database Module

PostgreSQL with pgvector for semantic search of markdown documents.
"""

import asyncpg
from pgvector.asyncpg import register_vector
import logging
from typing import Optional, List
from datetime import datetime

from md_kb.config import get_config
from md_kb.models import MarkdownDocument
from md_kb.embeddings import EmbeddingService

logger = logging.getLogger(__name__)

# Global connection pool and embedding service
_pool = None
_embedding_service = None


async def get_pool():
    """
    Get or create async PostgreSQL connection pool.

    Returns:
        asyncpg.Pool: Connection pool
    """
    global _pool
    if _pool is None:
        config = get_config()
        _pool = await asyncpg.create_pool(config.get_postgres_uri())
        logger.debug("PostgreSQL connection pool created")
    return _pool


async def close_pool():
    """
    Close PostgreSQL connection pool.

    Must be called when done to prevent event loop issues.
    """
    global _pool
    if _pool is not None:
        try:
            await _pool.close()
        except Exception:
            pass
        _pool = None
        logger.debug("PostgreSQL connection pool closed")


async def get_embedding_service():
    """
    Get or create embedding service.

    Returns:
        EmbeddingService: Embedding service instance
    """
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service


async def init_db():
    """
    Initialize PostgreSQL database schema with pgvector.

    Creates markdown_documents table, embedding column, and vector index.
    """
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None

    pool = await get_pool()

    async with pool.acquire() as conn:
        # Enable pgvector extension
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        await register_vector(conn)
        logger.info("pgvector extension enabled")

        # Create markdown_documents table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS markdown_documents (
                id SERIAL PRIMARY KEY,
                file_path TEXT NOT NULL UNIQUE,
                checksum TEXT NOT NULL,
                content TEXT NOT NULL,
                embedding vector(768),
                indexed_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)

        # Add embedding column if not exists (for existing databases)
        await conn.execute("""
            ALTER TABLE markdown_documents
            ADD COLUMN IF NOT EXISTS embedding vector(768)
        """)
        logger.debug("Embedding column added (768 dimensions)")

        # Create IVFFlat index for fast vector similarity search
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_md_docs_embedding
            ON markdown_documents USING ivfflat (embedding vector_cosine_ops)
        """)
        logger.debug("Vector index created")

        # Create other indexes
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_md_docs_path ON markdown_documents(file_path)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_md_docs_checksum ON markdown_documents(checksum)")

    logger.info("PostgreSQL database initialized.")


async def ingest_document(document: MarkdownDocument) -> MarkdownDocument:
    """
    Ingest or update a markdown document with semantic embedding.

    Uses upsert strategy on file_path.

    Args:
        document: The markdown document to store

    Returns:
        MarkdownDocument: The document with database-assigned ID

    Raises:
        ValueError: If document validation fails
    """
    # Validate the document
    errors = document.validate()
    if errors:
        error_msg = f"Invalid document: {', '.join(errors)}"
        logger.error(error_msg)
        raise ValueError(error_msg)

    pool = await get_pool()
    emb_service = await get_embedding_service()

    # Generate embedding for document content
    embedding = await emb_service.generate_embedding(document.content)

    if embedding is None:
        raise ValueError("Failed to generate embedding for document")

    async with pool.acquire() as conn:
        # Upsert document on file_path
        result = await conn.fetchrow("""
            INSERT INTO markdown_documents (file_path, checksum, content, embedding)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (file_path) DO UPDATE
            SET checksum = EXCLUDED.checksum,
                content = EXCLUDED.content,
                embedding = EXCLUDED.embedding,
                updated_at = NOW()
            RETURNING id
        """, document.file_path, document.checksum, document.content, embedding)

        doc_id = result["id"]
        logger.info(f"Document ingested/updated: {document.file_path} (ID: {doc_id})")

        # Return the document with the assigned ID
        document.id = doc_id
        return document


async def get_document_by_path(file_path: str) -> Optional[MarkdownDocument]:
    """
    Get a document by its file path.

    Args:
        file_path: The document's file path

    Returns:
        MarkdownDocument: The document, or None if not found
    """
    pool = await get_pool()

    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM markdown_documents WHERE file_path = $1", file_path)

        if row:
            return _row_to_document(row)
        return None


async def get_document_count() -> int:
    """
    Query the total number of documents.

    Returns:
        int: The count of documents
    """
    pool = await get_pool()

    async with pool.acquire() as conn:
        result = await conn.fetchval("SELECT COUNT(*) FROM markdown_documents")
        count = result if result is not None else 0
        return count


async def get_all_documents(limit: Optional[int] = None, offset: int = 0) -> List[MarkdownDocument]:
    """
    Get all documents from the database with pagination.

    Args:
        limit: Maximum number of documents to return
        offset: Number of documents to skip

    Returns:
        List[MarkdownDocument]: List of documents
    """
    pool = await get_pool()

    async with pool.acquire() as conn:
        query = 'SELECT * FROM markdown_documents ORDER BY indexed_at DESC'

        if limit is not None:
            query += " LIMIT $1 OFFSET $2"
            rows = await conn.fetch(query, limit, offset)
        else:
            query += " OFFSET $1"
            rows = await conn.fetch(query, offset)

        documents = [_row_to_document(row) for row in rows]

        logger.debug(f"Retrieved {len(documents)} documents from database")
        return documents


async def delete_document(file_path: str) -> bool:
    """
    Delete a document from the database.

    Args:
        file_path: The document's file path

    Returns:
        bool: True if deleted, False if not found
    """
    pool = await get_pool()

    async with pool.acquire() as conn:
        result = await conn.execute("DELETE FROM markdown_documents WHERE file_path = $1", file_path)
        deleted = result == "DELETE 1"

        if deleted:
            logger.info(f"Document deleted: {file_path}")
        else:
            logger.warning(f"Document not found for deletion: {file_path}")

        return deleted


async def search_documents(
    query: str,
    limit: Optional[int] = None,
    offset: int = 0,
    max_distance: float = 0.5,
) -> List[MarkdownDocument]:
    """
    Semantic search using vector similarity.

    Searches documents by embedding similarity instead of exact text.

    Args:
        query: Search query
        limit: Maximum number of results
        offset: Number of results to skip
        max_distance: Maximum cosine distance for results (0.0 = identical, 2.0 = opposite)

    Returns:
        List[MarkdownDocument]: Matching documents
    """
    pool = await get_pool()
    emb_service = await get_embedding_service()

    # Generate embedding for query
    query_embedding = await emb_service.generate_embedding(query)

    if query_embedding is None:
        logger.error(f"Failed to generate embedding for query: {query}")
        return []

    async with pool.acquire() as conn:
        # Register vector codec for this connection
        await register_vector(conn)

        # Vector similarity search using cosine distance (<=>)
        # Filter by max_distance to only return sufficiently similar results
        sql = """
            SELECT *, embedding <=> $1 AS distance
            FROM markdown_documents
            WHERE embedding <=> $1 <= $2
            ORDER BY distance
        """

        if limit is not None:
            sql += " LIMIT $3 OFFSET $4"
            rows = await conn.fetch(sql, query_embedding, max_distance, limit, offset)
        else:
            sql += " OFFSET $3"
            rows = await conn.fetch(sql, query_embedding, max_distance, offset)

        results = [_row_to_document(row) for row in rows]

        logger.debug(f"Semantic search for '{query}' returned {len(results)} documents (max_distance={max_distance})")
        return results


def _row_to_document(row) -> MarkdownDocument:
    """
    Convert a PostgreSQL row to a MarkdownDocument object.

    Args:
        row: Database row

    Returns:
        MarkdownDocument: The document object
    """
    return MarkdownDocument(
        id=row["id"],
        file_path=row["file_path"],
        checksum=row["checksum"],
        content=row["content"],
        embedding=row["embedding"],
        indexed_at=row["indexed_at"].isoformat() if row["indexed_at"] else None,
        updated_at=row["updated_at"].isoformat() if row["updated_at"] else None,
    )
