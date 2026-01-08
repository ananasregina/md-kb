"""
Markdown Knowledge Base - Watcher Module

Watches markdown directory for file system changes using watchfiles.
"""

import logging
from pathlib import Path
from watchfiles import awatch, Change

from md_kb.config import get_config
from md_kb.indexer import index_file

logger = logging.getLogger(__name__)


async def watch_directory():
    """
    Watch markdown directory for changes and trigger indexing.

    Runs continuously until cancelled.
    """
    config = get_config()
    markdown_dir = config.get_markdown_dir()

    logger.info(f"Starting file watcher for {markdown_dir}")

    async for changes in awatch(markdown_dir, recursive=True):
        for change_type, path in changes:
            path_obj = Path(path)

            # Only process markdown files
            if path_obj.suffix.lower() != ".md":
                continue

            # Log the change
            if change_type == Change.added:
                logger.info(f"File added: {path}")
            elif change_type == Change.modified:
                logger.info(f"File modified: {path}")
            elif change_type == Change.deleted:
                logger.info(f"File deleted: {path}")
                # File deleted - will be cleaned up on next full index
                # For now, just log it
                continue

            # Index the changed file
            try:
                if change_type != Change.deleted:
                    await index_file(path)
            except Exception as e:
                logger.error(f"Error indexing {path}: {e}")
