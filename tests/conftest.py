"""
Shared fixtures for md-kb tests.
"""

import pytest
import asyncio
import os
import tempfile
from pathlib import Path
from typing import Generator, AsyncGenerator
import asyncpg

# Test database configuration
TEST_DB_NAME = "test_md_kb"
TEST_DB_USER = "test_mdkb_user"
TEST_DB_PASSWORD = "test_password"


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_database() -> AsyncGenerator[str, None]:
    """Create and cleanup test database."""
    # Create test database
    conn = await asyncpg.connect(
        user="postgres",
        password="postgres",
        database="postgres"
    )
    await conn.execute(f"DROP DATABASE IF EXISTS {TEST_DB_NAME}")
    await conn.execute(f"CREATE DATABASE {TEST_DB_NAME}")
    await conn.close()

    # Create test user
    conn = await asyncpg.connect(
        user="postgres",
        password="postgres",
        database="postgres"
    )
    await conn.execute(f"DROP USER IF EXISTS {TEST_DB_USER}")
    await conn.execute(f"CREATE USER {TEST_DB_USER} WITH PASSWORD '{TEST_DB_PASSWORD}'")
    await conn.execute(f"GRANT ALL PRIVILEGES ON DATABASE {TEST_DB_NAME} TO {TEST_DB_USER}")
    await conn.execute(f"ALTER USER {TEST_DB_USER} CREATEDB")
    await conn.close()

    # Enable pgvector
    conn = await asyncpg.connect(
        user=TEST_DB_USER,
        password=TEST_DB_PASSWORD,
        database=TEST_DB_NAME
    )
    await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
    await conn.close()

    yield TEST_DB_NAME

    # Cleanup
    conn = await asyncpg.connect(
        user="postgres",
        password="postgres",
        database="postgres"
    )
    await conn.execute(f"DROP DATABASE IF EXISTS {TEST_DB_NAME}")
    await conn.execute(f"DROP USER IF EXISTS {TEST_DB_USER}")
    await conn.close()


@pytest.fixture
def sample_markdown_files(tmp_path):
    """Create sample markdown files for testing."""
    md_files = {
        "doc1.md": "# Introduction to Python\n\nPython is a high-level, interpreted programming language.",
        "doc2.md": "# Async Programming\n\nAsyncio provides infrastructure for concurrent code.",
    }

    for filename, content in md_files.items():
        (tmp_path / filename).write_text(content)

    # Create subdirectory
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    (subdir / "doc3.md").write_text("# PostgreSQL Database\n\nPostgreSQL is a powerful database system.")

    return tmp_path


@pytest.fixture
def mock_env_vars(monkeypatch) -> None:
    """Set test environment variables."""
    monkeypatch.setenv("MDKB_DB_HOST", "localhost")
    monkeypatch.setenv("MDKB_DB_PORT", "5432")
    monkeypatch.setenv("MDKB_DB_NAME", TEST_DB_NAME)
    monkeypatch.setenv("MDKB_DB_USER", TEST_DB_USER)
    monkeypatch.setenv("MDKB_DB_PASSWORD", TEST_DB_PASSWORD)
    monkeypatch.setenv("EMBEDDING_URL", "http://127.0.0.1:1338/v1")
    monkeypatch.setenv("EMBEDDING_MODEL", "text-embedding-nomic-embed-text-v1.5-embedding")
    monkeypatch.setenv("EMBEDDING_DIMENSION", "768")
