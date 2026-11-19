"""
Phase 2 Unit & Integration Tests: Hybrid Legal Search, Embeddings & Judgment APIs
India Legal News Aggregator - Free-Tier Architecture (< 250 MB RAM)

Covers:
1. Deterministic 384-dim TF-IDF / Feature-Hashing Fallback Embeddings
2. Provider Switching and Graceful API Fallbacks
3. Reciprocal Rank Fusion (RRF, k=60) Mathematical Verification & Rank Merging
4. Parameterized Filter Query Construction (< 100ms) & Legal Term Extraction
5. Redis Caching & In-Memory Fallback Resilience
6. Core FastAPI REST Endpoints (Feed, Hybrid Search, Detail, Precedents, Metadata)
"""

import datetime
import math
import time
from collections.abc import Sequence
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from app.api.v1.judgments import (
    get_judgment_by_id,
    get_similar_judgments,
    list_categories,
    list_courts,
    list_judgments,
    search_judgments,
)
from app.main import app
from app.models.judgment import Judgment
from app.schemas.judgment import (
    JudgmentListResponse,
    JudgmentResponse,
    SearchResponse,
)
from app.services.cache_service import CacheService, cache_service
from app.services.embedding_service import (
    VECTOR_DIMENSION,
    EmbeddingService,
    embedding_service,
)
from app.services.legal_classifier import CANONICAL_CATEGORIES
from app.services.search_service import (
    SearchCandidate,
    SearchExecutionResult,
    SearchService,
    compute_rrf,
    extract_matched_terms,
    search_service,
)
from fastapi import HTTPException

# ==============================================================================
# Sample Judgment Fixture Generator
# ==============================================================================


def create_sample_judgment(
    id: UUID | None = None,
    title: str = "Arvind Kejriwal v. Directorate of Enforcement",
    court_code: str = "sc",
    court_name: str = "Supreme Court of India",
    court_level: int = 1,
    subject_category: str = "Criminal",
    judgment_date: datetime.date | None = None,
    tags: Sequence[str] | None = None,
    excerpt: str = "Interim bail granted under Section 438 CrPC and Article 21.",
) -> Judgment:
    jid = id or uuid4()
    return Judgment(
        id=jid,
        external_id=f"hash_{jid.hex[:16]}",
        title=title,
        short_title=title.split(" v. ")[0],
        court_code=court_code,
        court_name=court_name,
        court_level=court_level,
        judgment_date=judgment_date or datetime.date(2024, 7, 12),
        subject_category=subject_category,
        excerpt=excerpt,
        full_text=f"Full judgment content for {title}...",
        url=f"https://indiankanoon.org/doc/{jid.hex[:8]}/",
        parties=[{"role": "petitioner", "name": "Arvind Kejriwal"}],
        tags=list(tags or ["Section 438 CrPC", "Article 21"]),
        source="indiankanoon",
        is_archived=True,
        classification_confidence=0.94,
        created_at=datetime.datetime.now(datetime.UTC),
        updated_at=datetime.datetime.now(datetime.UTC),
    )


# ==============================================================================
# 1. Deterministic Embedding Service Tests (< 80 MB RAM, Zero Keys)
# ==============================================================================


class TestEmbeddingService:
    """Verifies deterministic 384-dimensional feature hashing and provider fallbacks."""

    def test_vector_dimension_is_384(self):
        text = "Anticipatory bail petition under Section 438 CrPC"
        vec = embedding_service.generate_deterministic_embedding(text)
        assert len(vec) == 384
        assert len(vec) == VECTOR_DIMENSION

    def test_vector_is_l2_normalized(self):
        texts = [
            "Section 438 CrPC bail",
            "Article 21 fundamental rights",
            "Cheque bounce Section 138 Negotiable Instruments Act",
            "Corporate insolvency resolution process IBC Section 7",
        ]
        for t in texts:
            vec = embedding_service.generate_deterministic_embedding(t)
            norm = math.sqrt(sum(x * x for x in vec))
            assert abs(norm - 1.0) < 1e-4, f"Vector L2 norm {norm} is not unit normalized for '{t}'"

    def test_deterministic_repeatability(self):
        text = "State of Maharashtra vs Union of India basic structure doctrine"
        vec1 = embedding_service.generate_deterministic_embedding(text)
        vec2 = embedding_service.generate_deterministic_embedding(text)
        assert vec1 == vec2, "Deterministic embedding generator must yield identical output for same input"

    def test_different_texts_produce_different_vectors(self):
        vec1 = embedding_service.generate_deterministic_embedding("Anticipatory bail application 438 CrPC")
        vec2 = embedding_service.generate_deterministic_embedding("Company merger Section 230 Companies Act")
        assert vec1 != vec2

    def test_empty_and_whitespace_inputs_safe(self):
        vec_empty = embedding_service.generate_deterministic_embedding("")
        vec_space = embedding_service.generate_deterministic_embedding("   \n\t  ")
        assert len(vec_empty) == 384
        assert len(vec_space) == 384
        norm_empty = math.sqrt(sum(x * x for x in vec_empty))
        assert abs(norm_empty - 1.0) < 1e-4

    def test_legal_semantic_cosine_similarity(self):
        """Texts with overlapping legal concepts/statutes must have higher cosine similarity."""
        v_bail_1 = embedding_service.generate_deterministic_embedding("Interim anticipatory bail under Section 438 CrPC")
        v_bail_2 = embedding_service.generate_deterministic_embedding("Grant of anticipatory bail in criminal appeal")
        v_tax = embedding_service.generate_deterministic_embedding("Goods and Services Tax GST assessment input credit")

        def cosine_sim(a, b):
            return sum(x * y for x, y in zip(a, b))

        sim_bail_related = cosine_sim(v_bail_1, v_bail_2)
        sim_bail_tax = cosine_sim(v_bail_1, v_tax)

        assert sim_bail_related > sim_bail_tax
        assert sim_bail_related > 0.15

    @pytest.mark.asyncio
    async def test_async_get_embedding_deterministic_provider(self):
        svc = EmbeddingService(provider="deterministic")
        vec = await svc.get_embedding("Section 482 BNSS quashing of criminal proceedings")
        assert len(vec) == 384
        norm = math.sqrt(sum(x * x for x in vec))
        assert abs(norm - 1.0) < 1e-4

    @pytest.mark.asyncio
    async def test_hf_provider_fallback_without_token(self):
        """When HF provider is selected but no token configured, falls back to deterministic."""
        svc = EmbeddingService(provider="hf", hf_token=None)
        vec = await svc.get_embedding("Article 32 writ petition habeas corpus")
        assert len(vec) == 384
        assert math.isclose(math.sqrt(sum(x * x for x in vec)), 1.0, rel_tol=1e-4)

    @pytest.mark.asyncio
    async def test_batch_embeddings(self):
        texts = [
            "Criminal Appeal Section 302 IPC",
            "Civil Suit Order VII Rule 11 CPC",
            "Divorce Section 13 Hindu Marriage Act",
        ]
        vecs = await embedding_service.get_embeddings(texts)
        assert len(vecs) == 3
        for v in vecs:
            assert len(v) == 384


# ==============================================================================
# 2. Reciprocal Rank Fusion (RRF, k=60) Mathematical Verification
# ==============================================================================


class TestReciprocalRankFusion:
    """Tests the multi-retrieval rank fusion mathematics."""

    def test_rrf_scoring_formula(self):
        """Verify RRF_score(d) = sum(1 / (k + rank)) for k=60."""
        id_doc = uuid4()
        kw = [{"id": id_doc, "title": "Doc A"}]
        sem = [{"id": id_doc, "title": "Doc A"}]

        fused = compute_rrf(kw, sem, k=60)
        assert len(fused) == 1
        expected = (1.0 / (60 + 1)) + (1.0 / (60 + 1))  # 2 / 61 = 0.0327868...
        assert abs(fused[0]["score"] - expected) < 1e-4
        assert fused[0]["keyword_rank"] == 1
        assert fused[0]["semantic_rank"] == 1

    def test_dual_ranked_candidate_boost(self):
        """Candidate present in both keyword and semantic searches beats candidate in only one."""
        id_both = uuid4()
        id_kw_only = uuid4()
        id_sem_only = uuid4()

        kw_list = [
            {"id": id_kw_only, "title": "Keyword Only #1"},
            {"id": id_both, "title": "Dual Match #2 in kw"},
        ]
        sem_list = [
            {"id": id_sem_only, "title": "Semantic Only #1"},
            {"id": id_both, "title": "Dual Match #2 in sem"},
        ]

        fused = compute_rrf(kw_list, sem_list, k=60)
        # Score of id_both: 1/(60+2) + 1/(60+2) = 2/62 = 0.032258
        # Score of id_kw_only: 1/(60+1) = 1/61 = 0.016393
        # Score of id_sem_only: 1/(60+1) = 1/61 = 0.016393
        assert fused[0]["id"] == id_both
        assert fused[0]["score"] > fused[1]["score"]

    def test_disjoint_candidates_handled_gracefully(self):
        id_a, id_b, id_c = uuid4(), uuid4(), uuid4()
        kw_list = [{"id": id_a, "title": "Doc A"}, {"id": id_b, "title": "Doc B"}]
        sem_list = [{"id": id_c, "title": "Doc C"}]

        fused = compute_rrf(kw_list, sem_list, k=60)
        assert len(fused) == 3
        ids = [item["id"] for item in fused]
        assert id_a in ids
        assert id_b in ids
        assert id_c in ids

    def test_custom_k_parameter(self):
        id_a = uuid4()
        kw = [{"id": id_a, "title": "Doc"}]
        sem = []
        fused = compute_rrf(kw, sem, k=20)
        assert abs(fused[0]["score"] - (1.0 / (20 + 1))) < 1e-4


# ==============================================================================
# 3. Search Service & Parameterized Filter Construction (< 100ms)
# ==============================================================================


class TestSearchServiceFilters:
    """Verifies fast query construction, SQL injection protection, and legal entity extraction."""

    def test_sub_100ms_query_construction(self):
        service = SearchService()
        t0 = time.perf_counter()
        for _ in range(500):
            where, params = service.build_filter_clauses(
                category="Criminal",
                court="delhi-hc",
                date_from=datetime.date(2024, 1, 1),
                date_to=datetime.date(2024, 12, 31),
                citation="Section 438 CrPC",
            )
        elapsed_ms = (time.perf_counter() - t0) * 1000
        # 500 query constructions must finish well under 100ms total (< 0.2ms each)
        assert elapsed_ms < 100.0
        assert "subject_category = :category" in where
        assert "court_code = :court" in where
        assert "judgment_date >= :date_from" in where
        assert "judgment_date <= :date_to" in where

    def test_sql_injection_defense_parameterization(self):
        service = SearchService()
        malicious_cat = "Criminal' OR '1'='1"
        malicious_court = "sc'; DROP TABLE judgments; --"

        where, params = service.build_filter_clauses(
            category=malicious_cat,
            court=malicious_court,
        )

        # Raw values should be placed in params dict, not raw interpolated SQL
        assert "DROP TABLE" not in where
        assert "'1'='1" not in where
        assert params["category"] == malicious_cat
        assert params["court"] == malicious_court.lower()

    def test_statutory_and_citation_matched_terms_extraction(self):
        q = "Plea seeking anticipatory bail under Section 438 CrPC or Section 482 BNSS in murder charge"
        terms = extract_matched_terms(q)
        assert any("438 CrPC" in t or "BNSS" in t for t in terms)
        assert any("bail" in t.lower() for t in terms)

    def test_article_21_constitution_terms_extraction(self):
        q = "Right to privacy and personal liberty under Article 21 of Constitution"
        terms = extract_matched_terms(q)
        assert any("Article 21" in t for t in terms)

    def test_ni_act_cheque_bounce_terms_extraction(self):
        q = "Dishonour of cheque complaint under Section 138 NI Act"
        terms = extract_matched_terms(q)
        assert any("138" in t for t in terms)

    @pytest.mark.asyncio
    async def test_search_mode_switching_keyword_only(self):
        service = SearchService()
        mock_session = AsyncMock()

        sample_rows = [
            {
                "id": uuid4(),
                "external_id": "ext1",
                "title": "Title 1",
                "short_title": "T1",
                "court_code": "sc",
                "court_name": "Supreme Court",
                "court_level": 1,
                "judgment_date": datetime.date(2024, 7, 1),
                "subject_category": "Criminal",
                "excerpt": "Excerpt 1",
                "url": "https://example.com/1",
                "tags": ["Section 438 CrPC"],
                "source": "sci",
                "rank_score": 0.85,
            }
        ]

        with patch.object(service, "execute_keyword_search", AsyncMock(return_value=sample_rows)):
            res = await service.search(mock_session, query="Section 438 CrPC", mode="keyword")
            assert res.query_type == "keyword"
            assert len(res.results) == 1
            assert res.results[0].keyword_rank == 1
            assert res.results[0].semantic_rank is None

    @pytest.mark.asyncio
    async def test_search_mode_switching_semantic_only(self):
        service = SearchService()
        mock_session = AsyncMock()

        sample_rows = [
            {
                "id": uuid4(),
                "external_id": "ext2",
                "title": "Title 2",
                "short_title": "T2",
                "court_code": "delhi-hc",
                "court_name": "High Court of Delhi",
                "court_level": 2,
                "judgment_date": datetime.date(2024, 7, 2),
                "subject_category": "Constitutional",
                "excerpt": "Excerpt 2",
                "url": "https://example.com/2",
                "tags": ["Article 21"],
                "source": "livelaw",
                "sim_score": 0.92,
            }
        ]

        with patch.object(service, "execute_semantic_search", AsyncMock(return_value=sample_rows)):
            res = await service.search(mock_session, query="Article 21 fundamental rights", mode="semantic")
            assert res.query_type == "semantic"
            assert len(res.results) == 1
            assert res.results[0].semantic_rank == 1
            assert res.results[0].keyword_rank is None

    @pytest.mark.asyncio
    async def test_out_of_domain_query_returns_zero_results(self):
        """When neither keyword nor semantic criteria are met, hybrid search returns empty without random results."""
        service = SearchService()
        mock_session = AsyncMock()

        # Both keyword and semantic searches return empty
        with patch.object(service, "execute_keyword_search", AsyncMock(return_value=[])), \
             patch.object(service, "execute_semantic_search", AsyncMock(return_value=[])):
            res = await service.search(mock_session, query="UPI", mode="hybrid")
            assert res.total == 0
            assert len(res.results) == 0
            assert res.matched_terms == []

    @pytest.mark.asyncio
    async def test_semantic_search_filters_below_min_similarity(self):
        """Verifies execute_semantic_search drops rows with sim_score < min_similarity."""
        service = SearchService()
        mock_session = AsyncMock()

        # Database returns rows, but their similarity is near 0
        mock_mapping_result = MagicMock()
        mock_mapping_result.mappings.return_value.all.return_value = [
            {"id": uuid4(), "title": "Bail Case", "sim_score": 0.02},
            {"id": uuid4(), "title": "Divorce Case", "sim_score": -0.05},
            {"id": uuid4(), "title": "UPI Guidelines", "sim_score": 0.45},
        ]
        mock_session.execute.return_value = mock_mapping_result

        filtered = await service.execute_semantic_search(
            session=mock_session,
            query_vector=[0.1] * 384,
            where_sql="is_archived = true",
            params={},
            min_similarity=0.08,
        )
        assert len(filtered) == 1
        assert filtered[0]["title"] == "UPI Guidelines"

    def test_extract_matched_terms_two_letter_acronyms(self):
        terms = extract_matched_terms("Investigation by ED under PMLA and IT Act before SC")
        assert "ED" in terms or "ed" in [t.lower() for t in terms]
        assert "SC" in terms or "sc" in [t.lower() for t in terms]


# ==============================================================================
# 4. Redis Caching & In-Memory Fallback Resilience
# ==============================================================================


class TestCacheService:
    """Verifies Redis caching and automatic in-memory TTL fallback when Redis is offline."""

    @pytest.mark.asyncio
    async def test_in_memory_fallback_set_get(self):
        cache = CacheService(redis_url="redis://localhost:9999/0")  # unreachable port
        key = f"test_key_{uuid4().hex}"
        data = {"count": 42, "status": "cached"}

        # Store in cache
        success = await cache.set_json(key, data, ttl_seconds=60)
        assert success is True

        # Retrieve from cache
        retrieved = await cache.get_json(key)
        assert retrieved is not None
        assert retrieved["count"] == 42
        assert retrieved["status"] == "cached"

    @pytest.mark.asyncio
    async def test_cache_miss_returns_none(self):
        cache = CacheService()
        res = await cache.get(f"non_existent_{uuid4().hex}")
        assert res is None

    @pytest.mark.asyncio
    async def test_cache_delete_and_clear(self):
        cache = CacheService()
        key = f"del_key_{uuid4().hex}"
        await cache.set(key, "temp_value", ttl_seconds=60)
        assert await cache.get(key) == "temp_value"

        await cache.delete(key)
        assert await cache.get(key) is None


# ==============================================================================
# 5. Core FastAPI Judgments Endpoints
# ==============================================================================


class TestJudgmentsAPIEndpoints:
    """Verifies all Phase 2 REST endpoints, query contracts, and response schemas."""

    @pytest.mark.asyncio
    async def test_get_categories_metadata(self):
        cats = await list_categories()
        assert len(cats) == 10
        names = [c.name for c in cats]
        for canonical in CANONICAL_CATEGORIES:
            assert canonical in names
        # Check descriptions populated
        for c in cats:
            assert c.description is not None
            assert len(c.description) > 5

    @pytest.mark.asyncio
    async def test_get_courts_metadata(self):
        courts = await list_courts()
        assert len(courts) >= 10
        codes = [c.code for c in courts]
        assert "sc" in codes
        assert "delhi-hc" in codes
        assert "bombay-hc" in codes
        assert "nclat" in codes
        assert "ngt" in codes

    @pytest.mark.asyncio
    async def test_list_judgments_feed_paginated(self):
        mock_session = AsyncMock()
        j1 = create_sample_judgment()
        j2 = create_sample_judgment()

        # Mock count result
        mock_count_res = MagicMock()
        mock_count_res.scalar_one_or_none.return_value = 2

        # Mock items result
        mock_items_res = MagicMock()
        mock_items_res.scalars.return_value.all.return_value = [j1, j2]

        mock_session.execute.side_effect = [mock_count_res, mock_items_res]

        # Reset cache to test DB execution
        await cache_service.clear()

        response = await list_judgments(
            category="Criminal",
            court="sc",
            limit=20,
            offset=0,
            db=mock_session,
        )

        assert isinstance(response, JudgmentListResponse)
        assert response.total == 2
        assert len(response.data) == 2
        assert response.limit == 20
        assert response.offset == 0
        assert response.data[0].id == j1.id

    @pytest.mark.asyncio
    async def test_get_judgment_by_id_found(self):
        mock_session = AsyncMock()
        j = create_sample_judgment()

        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = j
        mock_session.execute.return_value = mock_res

        resp = await get_judgment_by_id(id=j.id, db=mock_session)
        assert isinstance(resp, JudgmentResponse)
        assert resp.id == j.id
        assert resp.court_code == j.court_code
        assert resp.subject_category == j.subject_category

    @pytest.mark.asyncio
    async def test_get_judgment_by_id_not_found_raises_404(self):
        mock_session = AsyncMock()
        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_res

        missing_id = uuid4()
        with pytest.raises(HTTPException) as exc_info:
            await get_judgment_by_id(id=missing_id, db=mock_session)

        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_hybrid_search_endpoint(self):
        mock_session = AsyncMock()
        cand_id = uuid4()
        mock_exec_res = SearchExecutionResult(
            results=[
                SearchCandidate(
                    id=cand_id,
                    external_id="ext_search_1",
                    title="State of Haryana vs Bhajan Lal",
                    short_title="State vs Bhajan Lal",
                    court_code="sc",
                    court_name="Supreme Court of India",
                    court_level=1,
                    judgment_date=datetime.date(1992, 1, 1),
                    subject_category="Criminal",
                    excerpt="Guidelines for quashing FIR under Section 482 CrPC.",
                    url="https://indiankanoon.org/doc/100/",
                    tags=["Section 482 CrPC", "Quashing"],
                    source="indiankanoon",
                    score=0.032,
                    keyword_rank=1,
                    semantic_rank=2,
                )
            ],
            query_type="hybrid",
            matched_terms=["Section 482 CrPC"],
            total=1,
        )

        with patch.object(search_service, "search", AsyncMock(return_value=mock_exec_res)):
            res = await search_judgments(
                q="Section 482 CrPC quashing guidelines",
                mode="hybrid",
                category="Criminal",
                court="sc",
                limit=10,
                offset=0,
                db=mock_session,
            )

            assert isinstance(res, SearchResponse)
            assert res.query_type == "hybrid"
            assert len(res.results) == 1
            assert res.results[0].id == cand_id
            assert res.results[0].keyword_rank == 1
            assert res.results[0].semantic_rank == 2
            assert "Section 482 CrPC" in res.matched_terms

    @pytest.mark.asyncio
    async def test_get_similar_judgments_endpoint(self):
        mock_session = AsyncMock()
        target_id = uuid4()
        related_j = create_sample_judgment(title="Related Precedent 1")

        with patch.object(search_service, "find_similar_judgments", AsyncMock(return_value=[related_j])):
            res = await get_similar_judgments(id=target_id, limit=5, db=mock_session)
            assert len(res) == 1
            assert res[0].id == related_j.id

    def test_all_phase2_routes_registered_in_fastapi_openapi(self):
        openapi_schema = app.openapi()
        paths = openapi_schema["paths"]

        expected_routes = [
            "/api/v1/health",
            "/api/v1/judgments",
            "/api/v1/judgments/search",
            "/api/v1/search",
            "/api/v1/judgments/{id}",
            "/api/v1/similar/{id}",
            "/api/v1/categories",
            "/api/v1/courts",
        ]
        for route in expected_routes:
            assert route in paths, f"Route {route} missing from FastAPI OpenAPI registration"
