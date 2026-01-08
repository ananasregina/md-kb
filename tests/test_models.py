"""
MarkdownDocument model tests.
"""

import pytest
from md_kb.models import MarkdownDocument


class TestMarkdownDocument:
    """Test MarkdownDocument dataclass."""

    def test_markdown_document_creation(self):
        """Test basic document creation."""
        doc = MarkdownDocument(
            id=1,
            file_path="/test/path.md",
            checksum="abc123",
            content="# Test",
        )

        assert doc.id == 1
        assert doc.file_path == "/test/path.md"
        assert doc.checksum == "abc123"
        assert doc.content == "# Test"

    def test_markdown_document_validation_empty(self):
        """Test validation errors for empty fields."""
        doc = MarkdownDocument(
            file_path="",
            checksum="",
            content="",
        )

        errors = doc.validate()

        assert len(errors) == 3
        assert any("file_path" in e for e in errors)
        assert any("checksum" in e for e in errors)
        assert any("content" in e for e in errors)

    def test_markdown_document_validation_missing_file_path(self):
        """Test missing required fields."""
        doc = MarkdownDocument(
            file_path="",
            checksum="abc123",
            content="# Test",
        )

        errors = doc.validate()

        assert any("file_path" in e for e in errors)

    def test_markdown_document_validation_missing_checksum(self):
        """Test missing checksum."""
        doc = MarkdownDocument(
            file_path="/test.md",
            checksum="",
            content="# Test",
        )

        errors = doc.validate()

        assert any("checksum" in e for e in errors)

    def test_markdown_document_validation_missing_content(self):
        """Test missing content."""
        doc = MarkdownDocument(
            file_path="/test.md",
            checksum="abc123",
            content="",
        )

        errors = doc.validate()

        assert any("content" in e for e in errors)

    def test_markdown_document_validation_valid(self):
        """Test valid document passes validation."""
        doc = MarkdownDocument(
            file_path="/test.md",
            checksum="abc123",
            content="# Test content",
            indexed_at="2026-01-08T00:00:00Z",
            updated_at="2026-01-08T00:00:00Z",
        )

        errors = doc.validate()

        assert len(errors) == 0

    def test_markdown_document_to_dict(self):
        """Test serialization to dictionary."""
        doc = MarkdownDocument(
            id=42,
            file_path="/test.md",
            checksum="abc123",
            content="# Test",
        )

        doc_dict = doc.to_dict()

        assert doc_dict["id"] == 42
        assert doc_dict["file_path"] == "/test.md"
        assert doc_dict["checksum"] == "abc123"
        assert doc_dict["content"] == "# Test"

    def test_markdown_document_from_dict(self):
        """Test deserialization from dictionary."""
        doc_dict = {
            "id": 42,
            "file_path": "/test.md",
            "checksum": "abc123",
            "content": "# Test",
            "embedding": [0.1, 0.2, 0.3],
        }

        doc = MarkdownDocument.from_dict(doc_dict)

        assert doc.id == 42
        assert doc.file_path == "/test.md"
        assert doc.checksum == "abc123"
        assert doc.content == "# Test"
        assert doc.embedding == [0.1, 0.2, 0.3]

    def test_markdown_document_str_repr(self):
        """Test __str__ output."""
        doc = MarkdownDocument(
            id=42,
            file_path="/path/to/document.md",
            checksum="abc123",
            content="# Test",
        )

        str_repr = str(doc)

        assert "MarkdownDocument" in str_repr
        assert "id=42" in str_repr
        assert "file_path='/path/to/document.md'" in str_repr

    def test_markdown_document_repr(self):
        """Test __repr__ output."""
        doc = MarkdownDocument(
            id=42,
            file_path="/very/long/path/to/document.md",
            checksum="abcdef1234567890abcdef1234567890",
            content="# Test content here",
        )

        repr_str = repr(doc)

        assert "MarkdownDocument" in repr_str
        assert "id=42" in repr_str
        assert len(repr_str) < 100
