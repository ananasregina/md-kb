"""
Markdown Knowledge Base - Embedding Service

Generates vector embeddings for markdown documents.
Uses LM Studio's OpenAI-compatible API.
"""

import logging
import asyncio
from typing import Optional
from openai import AsyncOpenAI

from md_kb.config import get_config

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Generate embeddings using LM Studio (OpenAI-compatible API).

    Transforms markdown text into vectors for semantic search.
    """

    def __init__(self):
        config = get_config()
        embedding_config = config.get_embedding_config()

        self.client = AsyncOpenAI(
            base_url=embedding_config["url"],
            api_key="not-required",
        )
        self.model = embedding_config["model"]
        self.dimension = embedding_config["dimension"]

        logger.debug(f"Embedding service initialized: {self.model} ({self.dimension}d)")

    async def generate_embedding(self, text: str) -> Optional[list[float]]:
        """
        Generate embedding for a single text string.

        Args:
            text: Text to embed

        Returns:
            List[float]: Embedding vector, or None if failed
        """
        try:
            response = await self.client.embeddings.create(
                input=text,
                model=self.model,
                encoding_format="float",
            )
            embedding = response.data[0].embedding

            logger.debug(f"Generated embedding for '{text[:30]}...': {len(embedding)} dimensions")
            return embedding

        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return None

    async def generate_embeddings_batch(
        self,
        texts: list[str],
    ) -> list[Optional[list[float]]]:
        """
        Generate embeddings for multiple texts in parallel.

        Note: LM Studio may not support batch requests,
        so we use parallel individual calls.

        Args:
            texts: List of texts to embed

        Returns:
            List[List[float] or None]: Embedding vectors
        """
        tasks = [self.generate_embedding(text) for text in texts]
        return await asyncio.gather(*tasks)
