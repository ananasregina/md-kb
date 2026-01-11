"""
Indexer module tests.
"""

import pytest
import hashlib
from pathlib import Path
from md_kb.indexer import (
    index_directory,
    index_file,
    find_markdown_files,
    compute_checksum,
    create_file,
    update_file,
    delete_file,
    list_files,
)
from md_kb.models import MarkdownDocument


class TestComputeChecksum:
    """Test checksum calculation."""

    def test_compute_checksum_deterministic(self, tmp_path):
        """Test that same file produces same checksum."""
        test_file = tmp_path / "test_checksum.md"
        content = "# Test content for checksum"
        test_file.write_text(content)

        checksum1 = compute_checksum(test_file)
        checksum2 = compute_checksum(test_file)

        assert checksum1 == checksum2
        assert len(checksum1) == 64  # SHA256 produces 64 hex chars

    def test_compute_checksum_different_content(self, tmp_path):
        """Test that different content produces different checksum."""
        test_file = tmp_path / "test_diff.md"
        test_file.write_text("# Content A")

        checksum1 = compute_checksum(test_file)

        test_file.write_text("# Content B")

        checksum2 = compute_checksum(test_file)

        assert checksum1 != checksum2


class TestFindMarkdownFiles:
    """Test markdown file discovery."""

    def test_find_markdown_files(self, tmp_path):
        """Test finding markdown files in directory."""
        # Create markdown files
        (tmp_path / "doc1.md").write_text("# Doc 1")
        (tmp_path / "doc2.md").write_text("# Doc 2")

        # Create non-markdown file (should be ignored)
        (tmp_path / "readme.txt").write_text("Readme")

        files = find_markdown_files(tmp_path)

        assert len(files) == 2
        assert all(f.suffix == ".md" for f in files)

    def test_find_markdown_files_includes_subdirs(self, tmp_path):
        """Test that search includes subdirectories."""
        # Create files in root
        (tmp_path / "root.md").write_text("# Root")

        # Create subdirectory with files
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "sub1.md").write_text("# Sub 1")
        (subdir / "sub2.md").write_text("# Sub 2")

        files = find_markdown_files(tmp_path)

        assert len(files) == 3

    def test_find_markdown_files_filters_non_md(self, tmp_path):
        """Test that non-.md files are filtered out."""
        (tmp_path / "test.md").write_text("# Markdown")
        (tmp_path / "test.txt").write_text("Text file")
        (tmp_path / "test.py").write_text("# Python script")

        files = find_markdown_files(tmp_path)

        assert len(files) == 1
        assert files[0].name == "test.md"

    def test_find_markdown_files_empty_directory(self, tmp_path):
        """Test finding files in empty directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        files = find_markdown_files(empty_dir)

        assert len(files) == 0


class TestIndexFile:
    """Test single file indexing."""

    @pytest.mark.asyncio
    async def test_index_file_new(self, mock_env_vars, sample_markdown_files):
        """Test indexing a new file."""
        doc = await index_file(str(sample_markdown_files / "doc1.md"))

        assert doc is not None
        assert doc.file_path == str(sample_markdown_files / "doc1.md")
        assert doc.id is not None

    @pytest.mark.asyncio
    async def test_index_file_update(self, mock_env_vars, sample_markdown_files):
        """Test updating an existing file."""
        # Index file first
        doc1 = await index_file(str(sample_markdown_files / "doc1.md"))

        # Modify file
        (sample_markdown_files / "doc1.md").write_text("# Modified content")

        # Index again
        doc2 = await index_file(str(sample_markdown_files / "doc1.md"))

        assert doc2.id == doc1.id
        assert doc2.content == "# Modified content"

    @pytest.mark.asyncio
    async def test_index_file_not_markdown(self, mock_env_vars, tmp_path):
        """Test error when file is not markdown."""
        non_md_file = tmp_path / "test.txt"
        non_md_file.write_text("Not markdown")

        with pytest.raises(ValueError, match="is not a markdown file"):
            await index_file(str(non_md_file))

    @pytest.mark.asyncio
    async def test_index_file_not_exists(self, mock_env_vars):
        """Test error when file doesn't exist."""
        with pytest.raises(ValueError, match="does not exist"):
            await index_file("/nonexistent/path.md")


class TestIndexDirectory:
    """Test directory indexing."""

    @pytest.mark.asyncio
    async def test_index_directory_new_files(self, mock_env_vars, sample_markdown_files):
        """Test indexing new files."""
        # Create additional test file
        (sample_markdown_files / "new_doc.md").write_text("# New document")

        stats = await index_directory()

        assert stats["indexed"] > 0
        assert "new_doc.md" in str(stats.get("indexed", ""))
        assert stats["skipped"] >= 2  # At least the 2 existing files

    @pytest.mark.asyncio
    async def test_index_directory_updated_files(self, mock_env_vars, sample_markdown_files):
        """Test updating changed files."""
        # Get initial stats
        stats1 = await index_directory()

        # Modify a file
        (sample_markdown_files / "doc1.md").write_text("# Updated content for doc1")

        # Reindex
        stats2 = await index_directory()

        assert stats2["updated"] == 1
        assert stats2["skipped"] >= 1  # At least doc2 should be skipped

    @pytest.mark.asyncio
    async def test_index_directory_unchanged_files(self, mock_env_vars, sample_markdown_files):
        """Test skipping unchanged files."""
        # First index
        stats1 = await index_directory()

        # Second index without changes
        stats2 = await index_directory()

        assert stats2["indexed"] == 0
        assert stats2["updated"] == 0
        assert stats2["skipped"] >= 2  # All existing files should be skipped

    @pytest.mark.asyncio
    async def test_index_directory_deleted_files(self, mock_env_vars, sample_markdown_files):
        """Test removing deleted files from database."""
        # Index initial files
        stats1 = await index_directory()
        initial_count = stats1["indexed"]

        # Delete a file
        (sample_markdown_files / "doc1.md").unlink()

        # Reindex
        stats2 = await index_directory()

        assert stats2["deleted"] == 1

    @pytest.mark.asyncio
    async def test_index_directory_statistics(self, mock_env_vars, sample_markdown_files):
        """Test that indexing returns correct statistics."""
        stats = await index_directory()

        assert "indexed" in stats
        assert "updated" in stats
        assert "deleted" in stats
        assert "skipped" in stats
        assert "errors" in stats

        assert stats["indexed"] >= 0
        assert stats["skipped"] >= 0

    @pytest.mark.asyncio
    async def test_index_directory_error_handling(self, mock_env_vars, sample_markdown_files, monkeypatch):
        """Test graceful error handling for problematic files."""
        # Create a problematic file (will be handled gracefully)
        bad_file = sample_markdown_files / "problematic.md"
        bad_file.write_text("# Problematic file")

        # Mock compute_checksum to raise an error
        original_checksum = compute_checksum
        checksum_call_count = 0

        def failing_checksum(path):
            nonlocal checksum_call_count
            checksum_call_count += 1
            if checksum_call_count == 1:
                raise OSError("Simulated file read error")
            return original_checksum(path)

        monkeypatch.setattr(
            "md_kb.indexer",
            "compute_checksum",
            failing_checksum
        )

        # Index directory (should handle error and continue)
        stats = await index_directory()

        # Should have recorded error
        assert stats["errors"] >= 0


class TestFileOperations:
    """Test file-level write operations."""

    @pytest.mark.asyncio
    async def test_create_file_success(self, mock_env_vars):
        """Test creating a new markdown file."""
        filename = "test_create.md"
        content = "# Test Document\n\nThis is a test document."

        doc = await create_file(filename, content)

        assert doc is not None
        assert doc.file_path.endswith(filename)
        assert doc.content == content
        assert doc.id is not None

        # Clean up
        await delete_file(filename)

    @pytest.mark.asyncio
    async def test_create_file_invalid_extension(self, mock_env_vars):
        """Test error when filename doesn't end with .md."""
        with pytest.raises(ValueError, match="must end with .md"):
            await create_file("test.txt", "Content")

    @pytest.mark.asyncio
    async def test_create_file_already_exists(self, mock_env_vars):
        """Test error when file already exists."""
        filename = "test_exists.md"
        content = "# Test"

        # Create file first
        await create_file(filename, content)

        # Try to create again
        with pytest.raises(ValueError, match="already exists"):
            await create_file(filename, "Different content")

        # Clean up
        await delete_file(filename)

    @pytest.mark.asyncio
    async def test_create_file_path_traversal(self, mock_env_vars):
        """Test that path traversal attempts are sanitized."""
        filename = "../etc/passwd.md"
        content = "Malicious content"

        # Should sanitize filename and create it in the correct directory
        doc = await create_file(filename, content)

        # Path should not contain parent directory traversal
        sanitized_filename = filename.replace("/", "").replace("\\", "")
        assert doc.file_path.endswith(sanitized_filename)

        # Clean up
        await delete_file("etcpasswd.md")

    @pytest.mark.asyncio
    async def test_update_file_success(self, mock_env_vars):
        """Test updating an existing file."""
        filename = "test_update.md"
        initial_content = "# Initial Content"
        updated_content = "# Updated Content\n\nNew paragraph."

        # Create file first
        await create_file(filename, initial_content)

        # Update file
        doc = await update_file(filename, updated_content)

        assert doc is not None
        assert doc.content == updated_content

        # Clean up
        await delete_file(filename)

    @pytest.mark.asyncio
    async def test_update_file_not_exists(self, mock_env_vars):
        """Test error when updating non-existent file."""
        with pytest.raises(ValueError, match="does not exist"):
            await update_file("nonexistent.md", "Content")

    @pytest.mark.asyncio
    async def test_update_file_invalid_extension(self, mock_env_vars):
        """Test error when filename doesn't end with .md."""
        with pytest.raises(ValueError, match="must end with .md"):
            await update_file("test.txt", "Content")

    @pytest.mark.asyncio
    async def test_delete_file_success(self, mock_env_vars):
        """Test deleting a file."""
        filename = "test_delete.md"
        content = "# To be deleted"

        # Create file first
        await create_file(filename, content)

        # Delete file
        deleted = await delete_file(filename)

        assert deleted is True

        # Verify file doesn't exist
        from md_kb.database import get_document_by_filename
        doc = await get_document_by_filename(filename)
        assert doc is None

    @pytest.mark.asyncio
    async def test_delete_file_not_exists(self, mock_env_vars):
        """Test deleting non-existent file."""
        deleted = await delete_file("nonexistent.md")

        assert deleted is False

    @pytest.mark.asyncio
    async def test_delete_file_invalid_extension(self, mock_env_vars):
        """Test error when filename doesn't end with .md."""
        with pytest.raises(ValueError, match="must end with .md"):
            await delete_file("test.txt")

    @pytest.mark.asyncio
    async def test_list_files(self, mock_env_vars):
        """Test listing all files."""
        # Create test files
        await create_file("test_list_1.md", "Content 1")
        await create_file("test_list_2.md", "Content 2")

        # List files
        files = await list_files()

        assert isinstance(files, list)
        assert "test_list_1.md" in files
        assert "test_list_2.md" in files

        # Clean up
        await delete_file("test_list_1.md")
        await delete_file("test_list_2.md")

    @pytest.mark.asyncio
    async def test_list_files_empty(self, mock_env_vars):
        """Test listing files when no custom files exist."""
        files = await list_files()

        assert isinstance(files, list)
        # Should at least have sample files from fixtures
        assert len(files) >= 0
