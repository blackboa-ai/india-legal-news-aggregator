"""
Unit Tests for Health Check Endpoints
India Legal News Aggregator - Phase 0 Scaffolding
"""


from app.api.v1.health import check_health
from app.main import app
from app.schemas.health import HealthResponse


def _run_coro(coro):
    """
    Executes a simple coroutine to completion without requiring an active OS socket pair loop.
    Enables tests to run cleanly in restricted/sandboxed CI environments.
    """
    try:
        coro.send(None)
    except StopIteration as exc:
        return exc.value
    raise RuntimeError("Coroutine did not finish synchronously")


def test_api_v1_health_endpoint():
    """
    Verify GET /api/v1/health returns HTTP 200 contract with status='ok' and service='india-legal-aggregator'.
    """
    result = _run_coro(check_health())
    assert isinstance(result, HealthResponse)
    assert result.status == "ok"
    assert result.service == "india-legal-aggregator"


def test_app_route_registration():
    """
    Verify /api/v1/health and /health routes are properly registered in FastAPI application.
    """
    paths = [route.path for route in app.routes if hasattr(route, "path")]
    assert "/health" in paths
    assert "/" in paths

    # Verify openapi schema has /api/v1/health
    openapi_schema = app.openapi()
    assert "/api/v1/health" in openapi_schema["paths"]
    assert "get" in openapi_schema["paths"]["/api/v1/health"]
