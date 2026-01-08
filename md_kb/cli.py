"""
Markdown Knowledge Base - CLI Module

Command-line interface for semantic search.
"""

import typer
from typing import Optional
import logging
import asyncio

from md_kb.database import (
    init_db,
    search_documents,
    close_pool,
)
from md_kb.indexer import index_directory

app = typer.Typer(
    name="mdkb",
    help="Semantic search for markdown collections",
    add_completion=False,
)

logger = logging.getLogger(__name__)


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
    limit: Optional[int] = typer.Option(
        None,
        "--limit",
        "-l",
        help="Maximum number of results (default: all)",
    ),
    max_distance: float = typer.Option(
        0.5,
        "--max-distance",
        "-d",
        help="Maximum similarity threshold (0.0-2.0, lower = more similar, default: 0.5)",
    ),
):
    """
    Search markdown documents with semantic similarity.

    Forces full index refresh before searching.
    """
    async def _do_search():
        # Initialize database
        await init_db()

        # Force full index refresh (blocking)
        stats = await index_directory()
        typer.echo(
            f"Index updated: {stats['indexed']} new, {stats['updated']} updated, "
            f"{stats['deleted']} deleted, {stats['skipped']} skipped"
        )
        typer.echo()

        # Perform search
        results = await search_documents(
            query=query,
            limit=limit,
            max_distance=max_distance,
        )

        # Close connection pool
        await close_pool()

        return results

    # Run search
    results = asyncio.run(_do_search())

    # Display results
    if not results:
        typer.echo(f"No results found for '{query}'")
        raise typer.Exit(0)

    typer.echo(f"Found {len(results)} result(s) for '{query}':")
    typer.echo()

    for i, doc in enumerate(results, 1):
        typer.echo(f"{i}. {doc.file_path}")
        typer.echo(f"   Similarity: {max_distance - (doc.content if doc.embedding else 0):.4f}")

        # Show snippet (first 200 chars of content)
        snippet = doc.content[:200].replace("\n", " ")
        if len(doc.content) > 200:
            snippet += "..."
        typer.echo(f"   Snippet: {snippet}")
        typer.echo()


@app.callback()
def main(
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose logging"
    ),
):
    """
    Markdown Knowledge Base - Semantic search for markdown collections
    """
    # Set up logging
    log_level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level=log_level,
        format="%(levelname)s: %(message)s",
    )

    if verbose:
        logger.debug("Verbose logging enabled.")


if __name__ == "__main__":
    app()
