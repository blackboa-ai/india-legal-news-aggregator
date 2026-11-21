"""
Unit & Integration Tests: VIP API Key Gatekeeper & Public Abuse Shields (v2.1 Phase 3)

Tests:
1. Settings & Config parsing for AUTHORIZED_API_KEYS (comma-separated, JSON array, list) and rate limits.
2. VIP Security Dependency (get_api_client_tier):
   - Returns 'vip' when valid X-API-Key is passed.
   - Returns 'public' when X-API-Key is missing, invalid, or empty.
3. VIP API Key Unthrottled Search:
   - Valid X-API-Key can execute 40 rapid search queries with HTTP 200 and 0 throttled 429s.
4. Public Search Rate Limiting:
   - Anonymous caller without VIP key is allowed up to PUBLIC_SEARCH_RATE_LIMIT_PER_MINUTE.
   - Exceeding the rate limit returns HTTP 429 with specific error message.
   - Distinct IP addresses maintain independent rate limit buckets.
5. Hot Query Caching in search_service.search:
   - First search executes and stores in L1 cache with 900s TTL.
   - Repeated search hits cache without executing SQL statements on the DB session.
6. Production Hardening:
   - When ENVIRONMENT == 'production', Swagger /docs, /redoc, /openapi.json are disabled (404).
   - Insecure default JWT_SECRET raises RuntimeError during production lifespan startup.
   - Secure JWT_SECRET in production passes lifespan startup validation.
"""

import datetime
import hashlib
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import httpx
import pytest
from app.api.deps import get_api_client_tier
from app.api.v1.judgments import search_rate_limiter
from app.auth import RateLimiter
from app.core.config import Settings, settings
from app.main import create_application, lifespan
from app.services.cache_service import cache_service
from app.services.search_service import (
    SearchExecutionResult,
    search_service,
)
from fastapi import Request

# ==============================================================================
# 1. Configuration & Validator Tests
# ==============================================================================

class TestConfigAuthorizedAPIKeys:
    """Verifies parsing and validation of AUTHORIZED_API_KEYS and rate limit settings."""

    def test_comma_separated_keys_parsed_correctly(self):
        cfg = Settings(AUTHORIZED_API_KEYS="key_alpha, key_beta, key_gamma")
        assert cfg.AUTHORIZED_API_KEYS == ["key_alpha", "key_beta", "key_gamma"]

    def test_json_array_keys_parsed_correctly(self):
        cfg = Settings(AUTHORIZED_API_KEYS='["key_1", "key_2", "key_3"]')
        assert cfg.AUTHORIZED_API_KEYS == ["key_1", "key_2", "key_3"]

    def test_list_and_tuple_keys_preserved(self):
        cfg = Settings(AUTHORIZED_API_KEYS=["key_x", "key_y"])
        assert cfg.AUTHORIZED_API_KEYS == ["key_x", "key_y"]

    def test_empty_string_parsed_as_empty_list(self):
        cfg = Settings(AUTHORIZED_API_KEYS="")
        assert cfg.AUTHORIZED_API_KEYS == []

    def test_public_search_rate_limit_setting_default(self):
        assert settings.PUBLIC_SEARCH_RATE_LIMIT_PER_MINUTE == 30


# ==============================================================================
# 2. Dependency: get_api_client_tier Tests
# ==============================================================================

class TestGetApiClientTierDependency:
    """Tests VIP authorization tier resolution based on X-API-Key."""

    @pytest.fixture(autouse=True)
    def configure_keys(self):
        original_keys = list(settings.AUTHORIZED_API_KEYS)
        settings.AUTHORIZED_API_KEYS = ["secret-vip-key-101", "lawpro-partner-token"]
        yield
        settings.AUTHORIZED_API_KEYS = original_keys

    @pytest.mark.asyncio
    async def test_valid_vip_key_returns_vip_tier(self):
        scope = {"type": "http", "headers": [(b"x-api-key", b"secret-vip-key-101")]}
        req = Request(scope)
        tier = await get_api_client_tier(req)
        assert tier == "vip"

    @pytest.mark.asyncio
    async def test_valid_vip_key_with_whitespace_returns_vip_tier(self):
        scope = {"type": "http", "headers": [(b"x-api-key", b"  lawpro-partner-token  ")]}
        req = Request(scope)
        tier = await get_api_client_tier(req)
        assert tier == "vip"

    @pytest.mark.asyncio
    async def test_invalid_key_returns_public_tier(self):
        scope = {"type": "http", "headers": [(b"x-api-key", b"unauthorized-key")]}
        req = Request(scope)
        tier = await get_api_client_tier(req)
        assert tier == "public"

    @pytest.mark.asyncio
    async def test_missing_header_returns_public_tier(self):
        scope = {"type": "http", "headers": []}
        req = Request(scope)
        tier = await get_api_client_tier(req)
        assert tier == "public"


# ==============================================================================
# 3. RateLimiter Component Tests
# ==============================================================================

class TestRateLimiterComponent:
    """Tests the sliding window RateLimiter component and reset functionality."""

    @pytest.mark.asyncio
    async def test_rate_limiter_allows_under_limit(self):
        limiter = RateLimiter(requests_per_minute=5)
        for _ in range(5):
            assert await limiter.is_allowed("192.168.1.100") is True

    @pytest.mark.asyncio
    async def test_rate_limiter_blocks_above_limit(self):
        limiter = RateLimiter(requests_per_minute=3)
        assert await limiter.is_allowed("10.0.0.1") is True
        assert await limiter.is_allowed("10.0.0.1") is True
        assert await limiter.is_allowed("10.0.0.1") is True
        assert await limiter.is_allowed("10.0.0.1") is False

    @pytest.mark.asyncio
    async def test_rate_limiter_distinct_identifiers_independent(self):
        limiter = RateLimiter(requests_per_minute=2)
        assert await limiter.is_allowed("user_a") is True
        assert await limiter.is_allowed("user_a") is True
        assert await limiter.is_allowed("user_a") is False

        # user_b has its own independent bucket
        assert await limiter.is_allowed("user_b") is True
        assert await limiter.is_allowed("user_b") is True
        assert await limiter.is_allowed("user_b") is False

    @pytest.mark.asyncio
    async def test_rate_limiter_reset_clears_timestamps(self):
        limiter = RateLimiter(requests_per_minute=2)
        assert await limiter.is_allowed("ip_reset_test") is True
        assert await limiter.is_allowed("ip_reset_test") is True
        assert await limiter.is_allowed("ip_reset_test") is False

        limiter.reset()
        assert await limiter.is_allowed("ip_reset_test") is True


# ==============================================================================
# 4. End-to-End API Search Rate Limiting & VIP Gatekeeper
# ==============================================================================

class TestAPISearchSecurityAndRateLimiting:
    """Verifies VIP API bypass and public 429 throttling on search endpoints."""

    @pytest.fixture(autouse=True)
    def setup_environment(self):
        from app.core.database import get_db
        from app.main import app

        original_keys = list(settings.AUTHORIZED_API_KEYS)
        original_limit = settings.PUBLIC_SEARCH_RATE_LIMIT_PER_MINUTE

        settings.AUTHORIZED_API_KEYS = ["vip-key-unlimited-access-999"]
        settings.PUBLIC_SEARCH_RATE_LIMIT_PER_MINUTE = 30
        search_rate_limiter.requests_per_minute = 30
        search_rate_limiter.reset()

        # Mock DB session for search endpoint
        async def mock_get_db():
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.mappings.return_value.all.return_value = []
            mock_result.scalar_one_or_none.return_value = 0
            mock_session.execute.return_value = mock_result
            yield mock_session

        app.dependency_overrides[get_db] = mock_get_db
        self.app = app

        yield

        app.dependency_overrides.pop(get_db, None)
        settings.AUTHORIZED_API_KEYS = original_keys
        settings.PUBLIC_SEARCH_RATE_LIMIT_PER_MINUTE = original_limit
        search_rate_limiter.requests_per_minute = original_limit
        search_rate_limiter.reset()

    @pytest.mark.asyncio
    async def test_vip_api_key_allows_40_rapid_search_queries_unthrottled(self):
        """VIP key allows 40 consecutive rapid searches without 429 HTTP error."""
        await cache_service.clear()
        search_rate_limiter.reset()

        # Mock search_service.search to return fast dummy result
        mock_result = SearchExecutionResult(
            results=[],
            query_type="hybrid",
            matched_terms=["constitution"],
            total=0,
        )

        with patch.object(search_service, "search", AsyncMock(return_value=mock_result)):
            transport = httpx.ASGITransport(app=self.app)
            async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
                headers = {"X-API-Key": "vip-key-unlimited-access-999"}
                for i in range(40):
                    resp = await client.get(
                        f"/api/v1/search?q=constitution_query_{i}",
                        headers=headers,
                    )
                    assert resp.status_code == 200, f"Query {i} throttled with status {resp.status_code}"

    @pytest.mark.asyncio
    async def test_anonymous_caller_throttled_at_limit_with_429(self):
        """Anonymous caller without VIP key hits 429 when exceeding rate limit."""
        await cache_service.clear()
        search_rate_limiter.reset()

        # Set limit to 5 for deterministic speed in test
        settings.PUBLIC_SEARCH_RATE_LIMIT_PER_MINUTE = 5
        search_rate_limiter.requests_per_minute = 5

        mock_result = SearchExecutionResult(
            results=[],
            query_type="hybrid",
            matched_terms=["bail"],
            total=0,
        )

        with patch.object(search_service, "search", AsyncMock(return_value=mock_result)):
            transport = httpx.ASGITransport(app=self.app)
            async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
                client_ip = "198.51.100.25"
                headers = {"X-Forwarded-For": client_ip}

                # First 5 requests should succeed
                for i in range(5):
                    resp = await client.get(
                        f"/api/v1/search?q=bail_query_{i}",
                        headers=headers,
                    )
                    assert resp.status_code == 200

                # 6th request from the same IP must receive HTTP 429
                blocked_resp = await client.get(
                    "/api/v1/search?q=bail_blocked",
                    headers=headers,
                )
                assert blocked_resp.status_code == 429
                data = blocked_resp.json()
                assert "Public search rate limit exceeded" in data.get("detail", "")

    @pytest.mark.asyncio
    async def test_judgments_search_alias_enforces_rate_limit(self):
        """GET /api/v1/judgments/search alias also respects public rate limit."""
        await cache_service.clear()
        search_rate_limiter.reset()

        settings.PUBLIC_SEARCH_RATE_LIMIT_PER_MINUTE = 2
        search_rate_limiter.requests_per_minute = 2

        mock_result = SearchExecutionResult(
            results=[],
            query_type="hybrid",
            matched_terms=["quash"],
            total=0,
        )

        with patch.object(search_service, "search", AsyncMock(return_value=mock_result)):
            transport = httpx.ASGITransport(app=self.app)
            async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
                headers = {"X-Forwarded-For": "203.0.113.88"}

                resp1 = await client.get("/api/v1/judgments/search?q=quash_1", headers=headers)
                assert resp1.status_code == 200

                resp2 = await client.get("/api/v1/judgments/search?q=quash_2", headers=headers)
                assert resp2.status_code == 200

                # 3rd request receives 429
                resp3 = await client.get("/api/v1/judgments/search?q=quash_3", headers=headers)
                assert resp3.status_code == 429


# ==============================================================================
# 5. Hot Query Caching in search_service.search
# ==============================================================================

class TestSearchServiceHotQueryCaching:
    """Verifies that search_service.search caches results and skips database execution on hits."""

    @pytest.fixture(autouse=True)
    async def setup_cache(self):
        await cache_service.clear()
        yield
        await cache_service.clear()

    @pytest.mark.asyncio
    async def test_search_service_caches_and_hits_without_db_call(self):
        """Second identical search query returns cached SearchExecutionResult without DB hit."""
        mock_session = AsyncMock()

        # Setup mock row execution
        candidate_id = uuid4()
        raw_row = {
            "id": candidate_id,
            "external_id": "test_ext_001",
            "title": "State of Maharashtra v. Union [Read Order]",
            "short_title": "State v. Union",
            "court_code": "sc",
            "court_name": "Supreme Court of India",
            "court_level": 1,
            "judgment_date": datetime.date(2024, 5, 10),
            "subject_category": "Constitutional",
            "excerpt": "Writ petition disposed.",
            "url": "https://example.com/test",
            "parties": [{"name": "State"}],
            "tags": ["article 32"],
            "source": "sci",
            "full_text": "Full text here...",
            "is_archived": True,
            "classification_confidence": 0.98,
            "content_type": "judgment",
            "content_type_confidence": 1.0,
            "created_at": datetime.datetime.now(datetime.timezone.utc),
            "updated_at": datetime.datetime.now(datetime.timezone.utc),
            "score": 0.85,
            "keyword_rank": 1,
            "semantic_rank": 1,
        }

        mock_mapping_res = MagicMock()
        mock_mapping_res.mappings.return_value.all.return_value = [raw_row]
        mock_session.execute.return_value = mock_mapping_res

        query = "State of Maharashtra"
        category = "Constitutional"
        content_type = "judgment"

        # 1. First execution - Cache Miss
        res1 = await search_service.search(
            session=mock_session,
            query=query,
            mode="keyword",
            category=category,
            content_type=content_type,
        )

        assert isinstance(res1, SearchExecutionResult)
        assert len(res1.results) == 1
        assert res1.results[0].title == "State of Maharashtra v. Union [Read Order]"
        assert mock_session.execute.call_count >= 1

        # Verify cache key structure
        expected_digest = hashlib.sha256(
            f"{category}:{None}:{None}:{None}:{None}:{content_type}".encode()
        ).hexdigest()
        cache_key = f"search:{query}:{10}:{0}:keyword:{expected_digest}"
        cached_entry = await cache_service.get_json(cache_key)
        assert cached_entry is not None

        # 2. Second execution - Cache Hit
        mock_session.execute.reset_mock()
        res2 = await search_service.search(
            session=mock_session,
            query=query,
            mode="keyword",
            category=category,
            content_type=content_type,
        )

        assert isinstance(res2, SearchExecutionResult)
        assert len(res2.results) == 1
        assert res2.results[0].title == res1.results[0].title
        # Critical verification: database session.execute was NEVER called on cache hit!
        assert mock_session.execute.call_count == 0


# ==============================================================================
# 6. Production Hardening: Swagger Lockdown & Insecure JWT Guard
# ==============================================================================

class TestProductionHardening:
    """Verifies production docs lockdown and startup security guardrails."""

    @pytest.mark.asyncio
    async def test_production_environment_disables_docs_and_openapi(self):
        """In production environment, /docs, /redoc, and /openapi.json return 404."""
        original_env = settings.ENVIRONMENT
        try:
            settings.ENVIRONMENT = "production"
            prod_app = create_application()

            # Verify FastAPI application configuration attributes
            assert prod_app.docs_url is None
            assert prod_app.redoc_url is None
            assert prod_app.openapi_url is None

            transport = httpx.ASGITransport(app=prod_app)
            async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
                r_docs = await client.get("/docs")
                assert r_docs.status_code == 404

                r_redoc = await client.get("/redoc")
                assert r_redoc.status_code == 404

                r_openapi = await client.get("/openapi.json")
                assert r_openapi.status_code == 404

                # Root index reflects docs: None in production
                r_root = await client.get("/")
                assert r_root.status_code == 200
                assert r_root.json().get("docs") is None
        finally:
            settings.ENVIRONMENT = original_env

    @pytest.mark.asyncio
    async def test_production_startup_raises_runtime_error_on_insecure_jwt_secret(self):
        """Production startup lifespan rejects default insecure JWT secret with RuntimeError."""
        original_env = settings.ENVIRONMENT
        original_jwt = settings.JWT_SECRET

        try:
            settings.ENVIRONMENT = "production"
            settings.JWT_SECRET = "insecure_dev_jwt_secret_key_change_in_production_min_32_characters"

            dummy_app = create_application()
            with pytest.raises(RuntimeError) as exc_info:
                async with lifespan(dummy_app):
                    pass

            assert "Insecure default JWT_SECRET cannot be used in production environment" in str(exc_info.value)
        finally:
            settings.ENVIRONMENT = original_env
            settings.JWT_SECRET = original_jwt

    @pytest.mark.asyncio
    async def test_production_startup_succeeds_with_secure_jwt_secret(self):
        """Production startup lifespan succeeds when strong JWT secret is configured."""
        original_env = settings.ENVIRONMENT
        original_jwt = settings.JWT_SECRET
        original_admin = settings.ADMIN_API_KEY

        try:
            settings.ENVIRONMENT = "production"
            settings.JWT_SECRET = "strong_production_entropy_secret_94812398412_safe"
            settings.ADMIN_API_KEY = "strong_production_admin_key_12345"

            dummy_app = create_application()
            async with lifespan(dummy_app):
                # Successfully entered lifespan without exception
                pass
        finally:
            settings.ENVIRONMENT = original_env
            settings.JWT_SECRET = original_jwt
            settings.ADMIN_API_KEY = original_admin
