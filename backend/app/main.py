"""
Main Application Entrypoint
India Legal News Aggregator - Free-Tier MVP Architecture (< 250 MB RAM)
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.api.v1.api import api_router
from app.core.config import settings
from app.services.cache_service import cache_service


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Lifespan context manager for application startup and graceful shutdown.
    Ensures Redis connections and background tasks are cleanly managed.
    """
    # Startup phase
    yield
    # Shutdown phase
    try:
        await cache_service.close()
    except Exception:
        pass


def create_application() -> FastAPI:
    """
    Factory to configure and instantiate the FastAPI application.
    Lightweight, high-performance, and configured for free-tier constraints.
    """
    application = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description="India Legal News Aggregator API - $0/month free-tier architecture with hybrid search.",
        openapi_url="/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
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

    # Mount API v1 router (provides /api/v1/health, /api/v1/judgments, /api/v1/auth, /api/v1/bookmarks, etc.)
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
            "docs": "/docs",
        }

    # Aliases for API documentation
    @application.get(f"{settings.API_V1_STR}/docs", include_in_schema=False)
    async def v1_docs_redirect():
        return RedirectResponse(url="/docs")

    @application.get(f"{settings.API_V1_STR}/openapi.json", include_in_schema=False)
    async def v1_openapi_redirect():
        return RedirectResponse(url="/openapi.json")

    return application


app = create_application()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
