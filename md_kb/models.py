"""
Markdown Knowledge Base - Data Models

Data models for markdown documents.
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, Any
import json


@dataclass
class MarkdownDocument:
    """
    A markdown document record.

    Represents a markdown file that has been indexed for semantic search.

    Attributes:
        id: The database-assigned ID
        file_path: Absolute path to the markdown file
        checksum: SHA256 checksum of file contents
        content: Full markdown file contents
        embedding: Vector embedding (768 dimensions for Nomic)
        indexed_at: When the document was first indexed
        updated_at: When the document was last updated
    """

    # Database fields
    id: Optional[int] = None

    # File information
    file_path: str = ""
    checksum: str = ""
    content: str = ""

    # Vector embedding
    embedding: Optional[list[float]] = None

    # Timestamps
    indexed_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """
        Convert document to dictionary.

        Returns:
            dict: The document as a dict (for JSON serialization)
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MarkdownDocument":
        """
        Create document from dictionary.

        Args:
            data: Dictionary representation of a document

        Returns:
            MarkdownDocument: A new document instance
        """
        return cls(**data)

    def validate(self) -> list[str]:
        """
        Validate the markdown document.

        Returns:
            list: List of error messages (empty if valid)
        """
        errors = []

        # file_path is required
        if not self.file_path:
            errors.append("file_path: This field is required")

        # checksum is required
        if not self.checksum:
            errors.append("checksum: This field is required")

        # content is required
        if not self.content:
            errors.append("content: This field is required")

        return errors

    def __str__(self) -> str:
        """
        String representation of document.

        Returns:
            str: Human-readable document description
        """
        return f"MarkdownDocument(id={self.id}, path='{self.file_path}')"

    def __repr__(self) -> str:
        """
        Developer representation of document.

        Returns:
            str: Unambiguous document representation
        """
        return f"MarkdownDocument(id={self.id}, file_path='{self.file_path}', checksum='{self.checksum[:16]}...')"
