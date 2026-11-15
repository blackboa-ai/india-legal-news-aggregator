"""
Search Suite Alias (Master Execution Plan Phase 2 Exit Gate)
India Legal News Aggregator - Free-Tier Architecture (< 250 MB RAM)

Re-exports Phase 2 Search, Embedding & Endpoint test suite matching
Master Execution Plan file reference.
"""

from tests.test_phase2_search import (
    TestCacheService,
    TestEmbeddingService,
    TestJudgmentsAPIEndpoints,
    TestReciprocalRankFusion,
    TestSearchServiceFilters,
)

__all__ = [
    "TestCacheService",
    "TestEmbeddingService",
    "TestJudgmentsAPIEndpoints",
    "TestReciprocalRankFusion",
    "TestSearchServiceFilters",
]
