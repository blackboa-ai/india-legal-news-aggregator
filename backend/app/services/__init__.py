"""
Services Package
Contains domain services: RSS ingestion, legal classification, lightweight embedding generator, and scheduler.
"""

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
]
