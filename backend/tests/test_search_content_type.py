"""
Unit & Integration Tests: Hybrid Search RRF Boost & Content Type API Filtering (v2.1 Phase 2)
Tests:
1. compute_rrf 1.15x ranking boost for 'judgment' items over 'news' items.
2. GET /api/v1/judgments?content_type=judgment returns HTTP 200 and judgment records.
3. GET /api/v1/judgments?content_type=news returns HTTP 200 and news records.
4. GET /api/v1/search?q=bail&content_type=judgment passes filter down to SQL.
5. Passing invalid content_type=invalid_foo returns HTTP 422 Unprocessable Entity.
6. Schema and dataclass validation for content_type and content_type_confidence.
"""

import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import httpx
import pytest
from app.api.v1.judgments import list_judgments, search_judgments
from app.main import app
from app.models.judgment import Judgment
from app.schemas.judgment import SearchResultItem
from app.services.cache_service import cache_service
from app.services.search_service import (
    SearchCandidate,
    compute_rrf,
    search_service,
)


def create_mock_candidate_dict(
    item_id: UUID | None = None,
    title: str = "Test Title",
    content_type: str = "unknown",
    content_type_confidence: float = 0.0,
    source: str = "livelaw",
) -> dict:
    """Helper creating raw candidate dictionaries mimicking SQL select rows."""
    cid = item_id or uuid4()
    return {
        "id": cid,
        "external_id": f"ext_{cid}",
        "title": title,
        "short_title": title[:50],
        "court_code": "sc",
        "court_name": "Supreme Court of India",
        "court_level": 1,
        "judgment_date": datetime.date(2024, 7, 1),
        "subject_category": "Criminal",
        "excerpt": f"Summary for {title}",
        "full_text": None,
        "url": f"https://example.com/{cid}",
        "parties": [],
        "tags": ["Bail"],
        "source": source,
        "is_archived": True,
        "classification_confidence": 0.9,
        "content_type": content_type,
        "content_type_confidence": content_type_confidence,
        "created_at": datetime.datetime.now(datetime.timezone.utc),
        "updated_at": datetime.datetime.now(datetime.timezone.utc),
    }


# ==============================================================================
# 1. RRF Ranking Boost Tests
# ==============================================================================

class TestComputeRRFJudgmentBoost:
    """Verifies that compute_rrf applies 1.15x boost to judgment items over news items."""

    def test_compute_rrf_applies_1_15x_boost_to_judgment_over_news(self):
        """
        When a judgment item and a news item have identical base rank scores,
        the 1.15x boost must elevate the judgment item to rank 1.
        """
        id_news = uuid4()
        id_judgment = uuid4()

        news_item = create_mock_candidate_dict(
            item_id=id_news,
            title="Collegium Recommends Judges",
            content_type="news",
            content_type_confidence=0.9,
        )
        judgment_item = create_mock_candidate_dict(
            item_id=id_judgment,
            title="State v. Accused [Read Order]",
            content_type="judgment",
            content_type_confidence=0.95,
        )

        # Equal reciprocal rank setup:
        # news: rank 1 in keyword, rank 2 in semantic -> 1/(60+1) + 1/(60+2)
        # judgment: rank 2 in keyword, rank 1 in semantic -> 1/(60+2) + 1/(60+1)
        keyword_items = [news_item, judgment_item]
        semantic_items = [judgment_item, news_item]

        base_score = (1.0 / (60 + 1)) + (1.0 / (60 + 2))
        expected_judgment_score = round(base_score * 1.15, 6)
        expected_news_score = round(base_score, 6)

        ranked = compute_rrf(
            keyword_items=keyword_items,
            semantic_items=semantic_items,
            k=60,
            apply_judgment_boost=True,
            judgment_boost_factor=1.15,
        )

        assert len(ranked) == 2
        # Judgment item must be ranked first due to 1.15x boost
        assert ranked[0]["id"] == id_judgment
        assert ranked[0]["content_type"] == "judgment"
        assert ranked[0]["score"] == expected_judgment_score

        # News item must be ranked second
        assert ranked[1]["id"] == id_news
        assert ranked[1]["content_type"] == "news"
        assert ranked[1]["score"] == expected_news_score

    def test_compute_rrf_boost_can_be_disabled(self):
        """When apply_judgment_boost=False, scores remain identical."""
        id_news = uuid4()
        id_judgment = uuid4()

        news_item = create_mock_candidate_dict(
            item_id=id_news,
            content_type="news",
        )
        judgment_item = create_mock_candidate_dict(
            item_id=id_judgment,
            content_type="judgment",
        )

        keyword_items = [news_item, judgment_item]
        semantic_items = [judgment_item, news_item]

        ranked = compute_rrf(
            keyword_items=keyword_items,
            semantic_items=semantic_items,
            k=60,
            apply_judgment_boost=False,
        )

        assert ranked[0]["score"] == ranked[1]["score"]

    def test_compute_rrf_custom_boost_factor(self):
        """Verify custom judgment_boost_factor values are correctly applied."""
        id_j = uuid4()
        j_item = create_mock_candidate_dict(item_id=id_j, content_type="judgment")

        ranked = compute_rrf(
            keyword_items=[j_item],
            semantic_items=[],
            k=60,
            apply_judgment_boost=True,
            judgment_boost_factor=1.25,
        )

        base_score = 1.0 / (60 + 1)
        expected_score = round(base_score * 1.25, 6)
        assert ranked[0]["score"] == expected_score


# ==============================================================================
# 2. Search Service SQL Filter & Dataclass Tests
# ==============================================================================

class TestSearchServiceFiltersAndDataclasses:
    """Verifies build_filter_clauses and SearchCandidate dataclass updates."""

    def test_build_filter_clauses_content_type_judgment(self):
        """build_filter_clauses adds content_type = :content_type and param."""
        where_sql, params = search_service.build_filter_clauses(
            category="Criminal",
            content_type="judgment",
        )
        assert "content_type = :content_type" in where_sql
        assert params["content_type"] == "judgment"
        assert params["category"] == "Criminal"

    def test_build_filter_clauses_content_type_news_case_insensitive(self):
        """content_type is trimmed and lowercased."""
        where_sql, params = search_service.build_filter_clauses(
            content_type=" NEWS ",
        )
        assert "content_type = :content_type" in where_sql
        assert params["content_type"] == "news"

    def test_build_filter_clauses_omits_content_type_when_none(self):
        """When content_type is None, no clause is appended."""
        where_sql, params = search_service.build_filter_clauses(content_type=None)
        assert "content_type" not in where_sql
        assert "content_type" not in params

    def test_search_candidate_dataclass_fields(self):
        """SearchCandidate includes content_type and content_type_confidence with defaults."""
        cid = uuid4()
        c = SearchCandidate(
            id=cid,
            external_id="ext_1",
            title="Title",
            short_title=None,
            court_code="sc",
            court_name="Supreme Court",
            court_level=1,
            judgment_date=datetime.date(2024, 1, 1),
            subject_category="Civil",
            excerpt="Excerpt",
            url="https://example.com/1",
        )
        assert c.content_type == "unknown"
        assert c.content_type_confidence == 0.0

    @pytest.mark.asyncio
    async def test_search_service_search_forwards_content_type(self):
        """search_service.search passes content_type to filter clause builder."""
        mock_session = AsyncMock()

        raw_row = create_mock_candidate_dict(
            title="State v. Accused",
            content_type="judgment",
            content_type_confidence=0.98,
        )

        with patch.object(search_service, "execute_keyword_search", AsyncMock(return_value=[raw_row])) as mock_kw:
            with patch.object(search_service, "execute_semantic_search", AsyncMock(return_value=[])):
                result = await search_service.search(
                    session=mock_session,
                    query="bail",
                    mode="hybrid",
                    content_type="judgment",
                )

                # Verify execute_keyword_search received where_sql containing content_type
                assert mock_kw.call_count == 1
                call_args = mock_kw.call_args[1]
                assert "content_type = :content_type" in call_args["where_sql"]
                assert call_args["params"]["content_type"] == "judgment"

                # Verify returned SearchCandidate mapped content_type fields
                assert len(result.results) == 1
                assert result.results[0].content_type == "judgment"
                assert result.results[0].content_type_confidence == 0.98


# ==============================================================================
# 3. GET /api/v1/judgments Content Type Filtering Tests
# ==============================================================================

class TestJudgmentsFeedContentTypeAPI:
    """Verifies content_type query parameter filtering on /api/v1/judgments."""

    @pytest.mark.asyncio
    async def test_get_judgments_filter_content_type_judgment(self):
        """GET /api/v1/judgments?content_type=judgment returns only judgment records."""
        await cache_service.clear()

        mock_session = AsyncMock()
        j_judgment = Judgment(
            id=uuid4(),
            external_id="j_ext_1",
            title="State v. ABC [Read Order]",
            court_code="sc",
            court_name="Supreme Court of India",
            court_level=1,
            judgment_date=datetime.date(2024, 7, 1),
            subject_category="Criminal",
            excerpt="Bail granted under Section 439 CrPC.",
            url="https://example.com/j1",
            source="livelaw",
            content_type="judgment",
            content_type_confidence=0.95,
        )

        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = [
            {
                "id": j_judgment.id,
                "external_id": j_judgment.external_id,
                "title": j_judgment.title,
                "short_title": j_judgment.short_title,
                "court_code": j_judgment.court_code,
                "court_name": j_judgment.court_name,
                "court_level": j_judgment.court_level,
                "judgment_date": j_judgment.judgment_date,
                "subject_category": j_judgment.subject_category,
                "excerpt": j_judgment.excerpt,
                "url": j_judgment.url,
                "tags": [],
                "source": j_judgment.source,
                "is_archived": True,
                "classification_confidence": 0.9,
                "content_type": "judgment",
                "content_type_confidence": 0.95,
                "created_at": datetime.datetime.now(datetime.timezone.utc),
                "updated_at": datetime.datetime.now(datetime.timezone.utc),
            }
        ]
        mock_session.execute.return_value = mock_result

        response = await list_judgments(
            content_type="judgment",
            db=mock_session,
        )

        assert response.total == 1
        assert len(response.data) == 1
        assert response.data[0].content_type == "judgment"
        assert response.data[0].content_type_confidence == 0.95

    @pytest.mark.asyncio
    async def test_get_judgments_filter_content_type_news(self):
        """GET /api/v1/judgments?content_type=news returns only news records."""
        await cache_service.clear()

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = [
            {
                "id": uuid4(),
                "external_id": "news_ext_1",
                "title": "Collegium Recommends 5 Names for High Courts",
                "short_title": "Collegium News",
                "court_code": "sc",
                "court_name": "Supreme Court of India",
                "court_level": 1,
                "judgment_date": datetime.date(2024, 7, 2),
                "subject_category": "Constitutional",
                "excerpt": "Collegium recommended appointments on Monday.",
                "url": "https://example.com/news1",
                "tags": [],
                "source": "barandbench",
                "is_archived": True,
                "classification_confidence": 0.85,
                "content_type": "news",
                "content_type_confidence": 0.92,
                "created_at": datetime.datetime.now(datetime.timezone.utc),
                "updated_at": datetime.datetime.now(datetime.timezone.utc),
            }
        ]
        mock_session.execute.return_value = mock_result

        response = await list_judgments(
            content_type="news",
            db=mock_session,
        )

        assert response.total == 1
        assert len(response.data) == 1
        assert response.data[0].content_type == "news"
        assert response.data[0].content_type_confidence == 0.92


# ==============================================================================
# 4. Search Endpoints Content Type Filtering Tests
# ==============================================================================

class TestSearchEndpointsContentTypeAPI:
    """Verifies content_type forwarding in /api/v1/search and /api/v1/judgments/search."""

    @pytest.mark.asyncio
    async def test_search_endpoint_passes_content_type_to_service(self):
        """GET /api/v1/search?q=bail&content_type=judgment passes filter to search_service."""
        await cache_service.clear()

        mock_session = AsyncMock()
        cand = SearchCandidate(
            id=uuid4(),
            external_id="c_1",
            title="State v. John Doe [Read Order]",
            short_title=None,
            court_code="sc",
            court_name="Supreme Court",
            court_level=1,
            judgment_date=datetime.date(2024, 7, 1),
            subject_category="Criminal",
            excerpt="Regular bail granted.",
            url="https://example.com/c1",
            content_type="judgment",
            content_type_confidence=0.96,
            score=0.035,
        )

        from app.services.search_service import SearchExecutionResult
        mock_exec_res = SearchExecutionResult(
            results=[cand],
            query_type="hybrid",
            matched_terms=["bail"],
            total=1,
        )

        with patch.object(search_service, "search", AsyncMock(return_value=mock_exec_res)) as mock_search:
            res = await search_judgments(
                q="bail",
                content_type="judgment",
                db=mock_session,
            )

            assert mock_search.call_count == 1
            call_kwargs = mock_search.call_args[1]
            assert call_kwargs["content_type"] == "judgment"
            assert call_kwargs["query"] == "bail"

            assert len(res.results) == 1
            assert res.results[0].content_type == "judgment"
            assert res.results[0].content_type_confidence == 0.96


# ==============================================================================
# 5. HTTP Validation: 422 Unprocessable Entity on Invalid content_type
# ==============================================================================

class TestHTTPContentTypeValidation:
    """Verifies that invalid content_type returns HTTP 422 Unprocessable Entity."""

    @pytest.fixture(autouse=True)
    def override_db(self):
        async def mock_get_db():
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.mappings.return_value.all.return_value = []
            mock_result.scalar_one_or_none.return_value = 0
            mock_session.execute.return_value = mock_result
            yield mock_session

        from app.core.database import get_db
        app.dependency_overrides[get_db] = mock_get_db
        yield
        app.dependency_overrides.pop(get_db, None)

    @pytest.mark.asyncio
    async def test_invalid_content_type_returns_422_on_feed(self):
        """Passing content_type=invalid_foo to /api/v1/judgments returns HTTP 422."""
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get("/api/v1/judgments?content_type=invalid_foo")
            assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_content_type_returns_422_on_search(self):
        """Passing content_type=invalid_foo to /api/v1/search returns HTTP 422."""
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get("/api/v1/search?q=bail&content_type=invalid_foo")
            assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_content_type_returns_422_on_judgments_search(self):
        """Passing content_type=invalid_foo to /api/v1/judgments/search returns HTTP 422."""
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get("/api/v1/judgments/search?q=bail&content_type=invalid_foo")
            assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_valid_content_types_pass_validation(self):
        """Values 'judgment', 'news', and 'unknown' pass query parameter validation."""
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            for c_type in ["judgment", "news", "unknown"]:
                # The endpoint will return 200 (or DB response), NOT 422 validation error
                response = await client.get(f"/api/v1/judgments?content_type={c_type}&limit=1")
                assert response.status_code != 422
