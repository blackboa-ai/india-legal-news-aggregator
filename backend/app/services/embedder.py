"""
Embedder Service Re-export
India Legal News Aggregator - Free-Tier Architecture (< 250 MB RAM)
Canonical alias matching Master Execution Plan architecture diagram.
"""

from app.services.embedding_service import (
    VECTOR_DIMENSION,
    EmbeddingService,
    embedding_service,
)

__all__ = ["VECTOR_DIMENSION", "EmbeddingService", "embedding_service"]
