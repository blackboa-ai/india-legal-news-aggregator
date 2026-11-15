"""
Services Package
Contains domain services: RSS ingestion, legal classification, lightweight embedding generator, hybrid search, caching, and scheduler.
"""

from app.services.cache_service import CacheService, cache_service
from app.services.embedding_service import (
    VECTOR_DIMENSION,
    EmbeddingService,
    embedding_service,
)
from app.services.legal_classifier import (
    CANONICAL_CATEGORIES,
    ClassificationResult,
    CourtInfo,
    LegalClassifier,
)
from app.services.rss_ingestor import (
    DEFAULT_LEGAL_FEEDS,
    FeedSourceConfig,
    ParsedJudgmentItem,
    RSSIngestor,
    canonicalize_url,
    compute_external_id,
    sanitize_html_text,
)
from app.services.scheduler import (
    get_scheduler,
    shutdown_scheduler,
    start_scheduler,
)
from app.services.search_service import (
    RRF_K_DEFAULT,
    SearchCandidate,
    SearchExecutionResult,
    SearchService,
    compute_rrf,
    extract_matched_terms,
    search_service,
)

__all__ = [
    "CANONICAL_CATEGORIES",
    "DEFAULT_LEGAL_FEEDS",
    "ClassificationResult",
    "CourtInfo",
    "FeedSourceConfig",
    "LegalClassifier",
    "ParsedJudgmentItem",
    "RSSIngestor",
    "canonicalize_url",
    "compute_external_id",
    "get_scheduler",
    "sanitize_html_text",
    "shutdown_scheduler",
    "start_scheduler",
    "EmbeddingService",
    "embedding_service",
    "VECTOR_DIMENSION",
    "SearchService",
    "search_service",
    "compute_rrf",
    "extract_matched_terms",
    "RRF_K_DEFAULT",
    "SearchCandidate",
    "SearchExecutionResult",
    "CacheService",
    "cache_service",
]
