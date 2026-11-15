"""
Test Ingestor Suite (Master Execution Plan Phase 1 Exit Gate)
India Legal News Aggregator - Free-Tier Architecture (< 250 MB RAM)

Re-exports and runs Phase 1 Ingestion and Classification test suite.
"""

from tests.test_phase1_ingestion import (
    TestDeduplication,
    TestFeedIngestion,
    TestHTMLSanitization,
    TestIngestionWorker,
    TestLegalClassifier,
)

__all__ = [
    "TestDeduplication",
    "TestFeedIngestion",
    "TestHTMLSanitization",
    "TestIngestionWorker",
    "TestLegalClassifier",
]
