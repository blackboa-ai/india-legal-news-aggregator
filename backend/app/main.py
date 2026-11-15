"""
Main Application Entrypoint
India Legal News Aggregator - Free-Tier MVP Architecture (< 250 MB RAM)
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.api import api_router
from app.core.config import settings


def create_application() -> FastAPI:
    """
    Factory to configure and instantiate the FastAPI application.
    Lightweight, high-performance, and configured for free-tier constraints.
    """
    application = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description="India Legal News Aggregator API - $0/month free-tier architecture with hybrid search.",
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url=f"{settings.API_V1_STR}/docs",
        redoc_url=f"{settings.API_V1_STR}/redoc",
    )

    # CORS Middleware Configuration
    if settings.CORS_ORIGINS:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=settings.CORS_ORIGINS,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Mount API v1 router (provides /api/v1/health and future v1 routes)
    application.include_router(api_router, prefix=settings.API_V1_STR)

    # Top-level health check endpoint for cloud platform probes (e.g., Render /health)
    @application.get(
        "/health",
        tags=["Health"],
        summary="Service Health Check",
        include_in_schema=False,
    )
    async def root_health():
        return {
            "status": "ok",
            "service": "india-legal-aggregator",
        }

    # Root index endpoint
    @application.get(
        "/",
        tags=["Root"],
        summary="Service Root Index",
        include_in_schema=False,
    )
    async def root_index():
        return {
            "service": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "status": "online",
            "docs": f"{settings.API_V1_STR}/docs",
        }

    return application


app = create_application()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
