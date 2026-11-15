"""
Health Check Router (v1)
"""

from fastapi import APIRouter

from app.schemas.health import HealthResponse

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check endpoint",
    description="Returns current service status and service identifier.",
)
async def check_health() -> HealthResponse:
    """
    GET /api/v1/health
    Returns: {"status": "ok", "service": "india-legal-aggregator"}
    """
    return HealthResponse(
        status="ok",
        service="india-legal-aggregator",
    )
