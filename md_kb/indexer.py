"""
Markdown Knowledge Base - Indexer Module

Scans markdown directory, computes checksums, and manages document indexing.
"""

import logging
import hashlib
from pathlib import Path
from typing import List, Dict
import asyncio

from md_kb.config import get_config
from md_kb.models import MarkdownDocument
from md_kb.database import ingest_document, get_document_by_path, delete_document, get_all_documents

logger = logging.getLogger(__name__)


def compute_checksum(file_path: Path) -> str:
    """
    Compute SHA256 checksum of file contents.

    Args:
        file_path: Path to the file

    Returns:
        str: SHA256 checksum as hex string
    """
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def find_markdown_files(directory: Path) -> List[Path]:
    """
    Find all markdown files in directory recursively.

    Args:
        directory: Root directory to scan

    Returns:
        List[Path]: List of markdown file paths
    """
    markdown_files = []
    for path in directory.rglob("*.md"):
        if path.is_file():
            markdown_files.append(path)
    return markdown_files


async def index_directory() -> Dict[str, int]:
    """
    Scan markdown directory, compute checksums, and upsert changes.

    Returns:
        Dict: Statistics about indexing {indexed: N, updated: M, deleted: K, skipped: L}
    """
    config = get_config()
    markdown_dir = config.get_markdown_dir()

    logger.info(f"Starting index of {markdown_dir}")

    # Find all markdown files
    markdown_files = find_markdown_files(markdown_dir)
    logger.info(f"Found {len(markdown_files)} markdown files")

    # Get existing documents from database
    existing_docs = await get_all_documents()
    existing_docs_by_path = {doc.file_path: doc for doc in existing_docs}
    logger.info(f"Found {len(existing_docs)} existing documents in database")

    # Statistics
    stats = {
        "indexed": 0,
        "updated": 0,
        "deleted": 0,
        "skipped": 0,
        "errors": 0,
    }

    # Process each markdown file
    for file_path in markdown_files:
        try:
            # Compute checksum
            checksum = compute_checksum(file_path)
            relative_path = file_path.relative_to(markdown_dir)
            file_path_str = str(file_path)

            # Read file content
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Check if document exists in database
            existing_doc = existing_docs_by_path.get(file_path_str)

            if existing_doc is None:
                # New file - insert
                doc = MarkdownDocument(
                    file_path=file_path_str,
                    checksum=checksum,
                    content=content,
                )
                await ingest_document(doc)
                stats["indexed"] += 1
                logger.debug(f"Indexed new file: {relative_path}")

            elif existing_doc.checksum != checksum:
                # File changed - update
                existing_doc.checksum = checksum
                existing_doc.content = content
                await ingest_document(existing_doc)
                stats["updated"] += 1
                logger.debug(f"Updated changed file: {relative_path}")

            else:
                # File unchanged - skip
                stats["skipped"] += 1
                logger.debug(f"Skipped unchanged file: {relative_path}")

        except Exception as e:
            stats["errors"] += 1
            logger.error(f"Error processing {file_path}: {e}")

    # Delete documents that no longer exist on disk
    disk_paths = {str(fp) for fp in markdown_files}
    for doc in existing_docs:
        if doc.file_path not in disk_paths:
            await delete_document(doc.file_path)
            stats["deleted"] += 1
            logger.debug(f"Deleted missing file: {doc.file_path}")

    logger.info(
        f"Index complete: {stats['indexed']} new, {stats['updated']} updated, "
        f"{stats['deleted']} deleted, {stats['skipped']} skipped, {stats['errors']} errors"
    )

    return stats


async def index_file(file_path: str) -> MarkdownDocument:
    """
    Index a single markdown file.

    Args:
        file_path: Path to the markdown file

    Returns:
        MarkdownDocument: The indexed document

    Raises:
        ValueError: If file is not a markdown file or doesn't exist
    """
    path = Path(file_path)

    if not path.exists():
        raise ValueError(f"File does not exist: {file_path}")

    if path.suffix.lower() != ".md":
        raise ValueError(f"File is not a markdown file: {file_path}")

    # Compute checksum
    checksum = compute_checksum(path)

    # Read file content
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # Check if document exists
    existing_doc = await get_document_by_path(file_path)

    if existing_doc is None:
        # New file
        doc = MarkdownDocument(
            file_path=file_path,
            checksum=checksum,
            content=content,
        )
    else:
        # Update existing
        existing_doc.checksum = checksum
        existing_doc.content = content
        doc = existing_doc

    # Ingest
    result = await ingest_document(doc)
    return result
