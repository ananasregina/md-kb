"""
Embedding service tests with real LM Studio integration.
"""

import pytest
from md_kb.embeddings import EmbeddingService


class TestEmbeddingService:
    """Test EmbeddingService with real LM Studio."""

    @pytest.mark.asyncio
    async def test_embedding_service_initialization(self, mock_env_vars):
        """Test EmbeddingService initialization."""
        service = EmbeddingService()

        assert service.client is not None
        assert service.model == "text-embedding-nomic-embed-text-v1.5-embedding"
        assert service.dimension == 768

    @pytest.mark.asyncio
    async def test_generate_embedding_success(self, mock_env_vars):
        """Test successful embedding generation with real LM Studio."""
        service = EmbeddingService()

        # Real API call to LM Studio
        embedding = await service.generate_embedding("test query")

        assert embedding is not None
        assert len(embedding) == 768
        assert all(isinstance(x, float) for x in embedding)

    @pytest.mark.asyncio
    async def test_generate_embedding_different_inputs(self, mock_env_vars):
        """Test embedding generation with different inputs."""
        service = EmbeddingService()

        # Test different inputs
        texts = [
            "Python programming",
            "Async/await syntax",
            "PostgreSQL database",
            "Short",
            "A much longer text with multiple sentences that should still generate valid embeddings without any issues.",
        ]

        for text in texts:
            embedding = await service.generate_embedding(text)
            assert embedding is not None
            assert len(embedding) == 768

    @pytest.mark.asyncio
    async def test_generate_embeddings_batch(self, mock_env_vars):
        """Test batch embedding generation."""
        service = EmbeddingService()

        texts = [
            "Document 1",
            "Document 2",
            "Document 3",
        ]

        embeddings = await service.generate_embeddings_batch(texts)

        assert len(embeddings) == 3
        for embedding in embeddings:
            assert embedding is not None
            assert len(embedding) == 768

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_generate_embedding_performance(self, mock_env_vars):
        """Test embedding generation performance."""
        import time

        service = EmbeddingService()

        start_time = time.time()
        embedding = await service.generate_embedding("performance test query")
        end_time = time.time()

        duration = end_time - start_time

        assert embedding is not None
        assert duration < 5.0  # Should complete within 5 seconds

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_generate_embeddings_batch_parallel(self, mock_env_vars):
        """Test that batch embeddings are generated in parallel."""
        import time

        service = EmbeddingService()

        texts = ["doc" + str(i) for i in range(10)]

        start_time = time.time()
        embeddings = await service.generate_embeddings_batch(texts)
        end_time = time.time()

        duration = end_time - start_time

        assert len(embeddings) == 10
        assert all(e is not None for e in embeddings)
        assert duration < 15.0  # 10 embeddings in < 15 seconds means parallel execution

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_embedding_consistency(self, mock_env_vars):
        """Test that same input produces consistent embeddings."""
        service = EmbeddingService()

        text = "consistency test text"

        # Generate embeddings multiple times
        embedding1 = await service.generate_embedding(text)
        embedding2 = await service.generate_embedding(text)
        embedding3 = await service.generate_embedding(text)

        assert embedding1 is not None
        assert embedding2 is not None
        assert embedding3 is not None

        # Check consistency (may have minor floating-point differences)
        for i in range(768):
            assert abs(embedding1[i] - embedding2[i]) < 0.01
            assert abs(embedding2[i] - embedding3[i]) < 0.01
