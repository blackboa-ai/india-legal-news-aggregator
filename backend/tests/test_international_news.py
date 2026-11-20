"""
Unit and Integration Tests for International Breaking News & API Shielding
India Legal News Aggregator - Free-Tier Architecture (< 250 MB RAM)

Verifies:
1. BBC World News RSS feed configuration in DEFAULT_LEGAL_FEEDS.
2. Deterministic classification of international breaking news into 'news' content type,
   'international' court code, and 'International' subject category.
3. API Shielding: Default generic queries (GET /api/v1/judgments) exclude international items
   so external apps querying for Indian legal judgments are untouched.
4. Filtered queries (GET /api/v1/judgments?court=international) return international breaking news.
5. SearchService builds correct parameter clauses with court_code != 'international' on default calls.
"""

import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.api.v1.judgments import INDIAN_COURTS, list_courts, list_judgments
from app.models.judgment import Judgment
from app.schemas.judgment import CourtItem, JudgmentListResponse
from app.services.legal_classifier import CourtInfo, LegalClassifier, classify_content_type
from app.services.rss_ingestor import DEFAULT_LEGAL_FEEDS, FeedSourceConfig
from app.services.search_service import SearchService


def test_bbc_feed_configured_in_default_feeds():
    """Verifies BBC World News feed is configured in DEFAULT_LEGAL_FEEDS."""
    bbc_feeds = [f for f in DEFAULT_LEGAL_FEEDS if f.source_id == "bbc"]
    assert len(bbc_feeds) == 1
    feed = bbc_feeds[0]
    assert feed.default_court_code == "international"
    assert feed.default_court_name == "International Breaking News"
    assert feed.default_court_level == 4
    assert feed.enabled is True
    assert "bbci.co.uk" in feed.url


def test_international_news_classification():
    """Verifies deterministic classification of international breaking news."""
    default_court = CourtInfo(
        court_code="international",
        court_name="International Breaking News",
        court_level=4,
    )
    title = "UN Climate Summit agrees on new global carbon offset standards"
    text = "Delegates at the international summit reached an agreement late Friday evening."
    url = "https://www.bbc.com/news/world-123456"

    # Test Court extraction stays international
    court = LegalClassifier.extract_court(title, default_court=default_court)
    assert court.court_code == "international"
    assert court.court_name == "International Breaking News"
    assert court.court_level == 4

    # Test full classification
    res = LegalClassifier.classify(
        title=title,
        text=text,
        source="bbc",
        default_court=default_court,
        url=url,
    )
    assert res.court.court_code == "international"
    assert res.court.court_level == 4
    assert res.subject_category == "International"
    assert res.content_type == "news"


def test_classify_content_type_for_bbc():
    """Verifies classify_content_type returns ('news', 1.0) for bbc source."""
    c_type, conf = classify_content_type(
        title="Breaking News Story Headline",
        text="World news report body text",
        source="bbc",
        url="https://www.bbc.com/news/world-123",
    )
    assert c_type == "news"
    assert conf == 1.0


def test_search_service_build_filter_clauses_international():
    """Verifies search clauses isolate international news on default and honor explicit court."""
    service = SearchService()

    # 1. Default call (no court, no category): must shield external app
    where_default, params_default = service.build_filter_clauses()
    assert "court_code != 'international'" in where_default
    assert "court" not in params_default

    # 2. Explicit court='international': must filter for international
    where_intl, params_intl = service.build_filter_clauses(court="international")
    assert "court_code = :court" in where_intl
    assert params_intl["court"] == "international"
    assert "court_code != 'international'" not in where_intl

    # 3. Explicit court='sc': must filter for sc
    where_sc, params_sc = service.build_filter_clauses(court="sc")
    assert "court_code = :court" in where_sc
    assert params_sc["court"] == "sc"
    assert "court_code != 'international'" not in where_sc

    # 4. Explicit category='International': must not exclude international
    where_cat, params_cat = service.build_filter_clauses(category="International")
    assert "court_code != 'international'" not in where_cat


@pytest.mark.asyncio
async def test_list_courts_includes_international():
    """Verifies GET /courts includes International Breaking News."""
    courts = await list_courts()
    intl = [c for c in courts if c.code == "international"]
    assert len(intl) == 1
    assert intl[0].name == "International Breaking News"
    assert intl[0].level == 4
