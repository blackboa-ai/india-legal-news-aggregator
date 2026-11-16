"""
Unit & Integration Tests for Production Hardening & Security Middleware (Phase 5)
India Legal News Aggregator - Free-Tier MVP Architecture (< 250 MB RAM)
"""

import httpx
import pytest
from app.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_security_headers_present_on_health():
    """
    Verify production security headers are injected by middleware on all responses:
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY
    - X-XSS-Protection: 1; mode=block
    - Referrer-Policy: strict-origin-when-cross-origin
    - Strict-Transport-Security: max-age=...
    - Content-Security-Policy: default-src 'self'
    - Permissions-Policy
    - X-Response-Time-Ms
    """
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/health")
        assert response.status_code == 200

        headers = response.headers
        assert headers.get("X-Content-Type-Options") == "nosniff"
        assert headers.get("X-Frame-Options") == "DENY"
        assert headers.get("X-XSS-Protection") == "1; mode=block"
        assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
        assert "Strict-Transport-Security" in headers
        assert "Content-Security-Policy" in headers
        assert "Permissions-Policy" in headers
        assert "X-Response-Time-Ms" in headers

        # Verify response body structure
        body = response.json()
        assert body["status"] == "ok"
        assert body["service"] == "india-legal-aggregator"


@pytest.mark.asyncio
async def test_root_health_endpoint():
    """Verify root /health endpoint responds with 200 OK and security headers."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert "X-Response-Time-Ms" in response.headers


@pytest.mark.asyncio
async def test_root_index_endpoint():
    """Verify root / endpoint responds with 200 OK and metadata."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "online"
        assert "version" in data


@pytest.mark.asyncio
async def test_clean_json_error_envelope_404():
    """
    Verify 404 Not Found returns a clean JSON error envelope without stack traces,
    while maintaining detail and error keys for frontend compatibility.
    """
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/non_existent_route_12345")
        assert response.status_code == 404

        data = response.json()
        assert "detail" in data
        assert "error" in data
        assert data["error"]["code"] == 404
        assert data["error"]["type"] == "http_error"

        # Security headers should also be present on error responses
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"


@pytest.mark.asyncio
async def test_clean_json_error_envelope_422():
    """
    Verify 422 Unprocessable Entity for invalid schemas returns a structured JSON error envelope.
    """
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Invalid JSON payload for registration (missing password)
        response = await client.post("/api/v1/auth/register", json={"email": "not-an-email"})
        assert response.status_code == 422

        data = response.json()
        assert "detail" in data
        assert "error" in data
        assert data["error"]["code"] == 422
        assert data["error"]["type"] == "validation_error"
        assert isinstance(data["error"]["details"], list)


@pytest.mark.asyncio
async def test_clean_json_error_envelope_500_without_stack_trace():
    """
    Verify unhandled exceptions return a clean 500 error envelope
    and never leak python tracebacks or internal paths.
    """
    # Create a temporary route on the application that simulates an unhandled server error
    @app.get("/api/v1/test-simulated-server-error", include_in_schema=False)
    async def simulated_error():
        raise RuntimeError("Simulated internal database crash or unhandled bug")

    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get("/api/v1/test-simulated-server-error")
            assert response.status_code == 500

            data = response.json()
            assert "detail" in data
            assert "error" in data
            assert data["error"]["code"] == 500
            assert data["error"]["type"] == "internal_server_error"

            # Crucial: verify internal exception text and traceback are NOT leaked to the client
            body_str = response.text
            assert "Simulated internal database crash" not in body_str
            assert "Traceback" not in body_str
            assert "RuntimeError" not in body_str

            # Verify security headers are attached
            assert response.headers.get("X-Content-Type-Options") == "nosniff"
            assert "X-Response-Time-Ms" in response.headers
    finally:
        # Clean up temporary test route
        app.routes[:] = [r for r in app.routes if getattr(r, "path", None) != "/api/v1/test-simulated-server-error"]
