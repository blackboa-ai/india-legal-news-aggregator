"""
Main Application Entrypoint
India Legal News Aggregator - Free-Tier MVP Architecture (< 250 MB RAM)
Includes production security headers middleware, structured request latency logging,
and global exception handlers returning clean JSON error envelopes.
"""

import logging
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.api import api_router
from app.core.config import settings
from app.services.cache_service import cache_service
from app.services.scheduler import shutdown_scheduler, start_scheduler

logger = logging.getLogger("app.main")
access_logger = logging.getLogger("app.access")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Lifespan context manager for application startup and graceful shutdown.
    Ensures Redis connections, APScheduler jobs, and background tasks are cleanly managed.
    """
    # Startup phase: validate production security configuration
    if settings.ENVIRONMENT.lower() == "production" and settings.JWT_SECRET.startswith("insecure_dev_jwt"):
        raise RuntimeError("FATAL: Insecure default JWT_SECRET cannot be used in production environment.")

    # Startup phase: start scheduler only in production/development, skip in test environment
    if settings.ENVIRONMENT != "test":
        try:
            start_scheduler(interval_minutes=20)
        except Exception as exc:
            logger.warning("Could not initialize APScheduler during startup: %s", exc)

    yield

    # Shutdown phase
    try:
        shutdown_scheduler()
    except Exception:
        pass
    try:
        await cache_service.close()
    except Exception:
        pass


def create_application() -> FastAPI:
    """
    Factory to configure and instantiate the FastAPI application.
    Lightweight, high-performance, and configured for free-tier constraints.
    Includes security headers middleware, request latency tracking, and global error handling.
    """
    is_prod = settings.ENVIRONMENT.lower() == "production"

    application = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description="India Legal News Aggregator API - $0/month free-tier architecture with hybrid search.",
        openapi_url=None if is_prod else "/openapi.json",
        docs_url=None if is_prod else "/docs",
        redoc_url=None if is_prod else "/redoc",
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

    # GZip compression middleware (compresses response payloads >= 500 bytes)
    application.add_middleware(GZipMiddleware, minimum_size=500)

    # Production Security Headers & Structured Request Latency Logging Middleware
    @application.middleware("http")
    async def security_and_latency_middleware(request: Request, call_next):
        """
        1. Tracks execution duration and logs structured latency metrics.
        2. Injects standard production HTTP security headers on all responses.
        3. Exposes X-Response-Time-Ms header for diagnostics.
        """
        start_time = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception as exc:
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            logger.exception(
                "Unhandled exception during request processing (%s %s): %s",
                request.method,
                request.url.path,
                exc,
            )
            response = JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "detail": "An internal server error occurred. Please try again later.",
                    "error": {
                        "code": 500,
                        "message": "An internal server error occurred. Please try again later.",
                        "type": "internal_server_error",
                    },
                },
            )

        latency_ms = (time.perf_counter() - start_time) * 1000.0

        # Production Security Headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), camera=(), geolocation=(), gyroscope=(), "
            "magnetometer=(), microphone=(), payment=(), usb=()"
        )
        response.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'none';"
        response.headers["X-Response-Time-Ms"] = f"{latency_ms:.2f}"

        # Public feed/search caching headers (HTTP Cache-Control: public, max-age=30, stale-while-revalidate=60)
        if request.method == "GET" and response.status_code == 200:
            path = request.url.path
            is_feed_or_search = (
                path.startswith(f"{settings.API_V1_STR}/judgments")
                or path.startswith(f"{settings.API_V1_STR}/search")
                or path.startswith(f"{settings.API_V1_STR}/similar")
                or path.startswith(f"{settings.API_V1_STR}/categories")
                or path.startswith(f"{settings.API_V1_STR}/courts")
                or path in ("/categories", "/courts", "/search", "/judgments")
            )
            if is_feed_or_search and "Cache-Control" not in response.headers:
                response.headers["Cache-Control"] = "public, max-age=30, stale-while-revalidate=60"

        # Structured request latency logging
        client_ip = request.client.host if request.client else "unknown"
        access_logger.info(
            "request_completed method=%s path=%s status=%d latency_ms=%.2f client=%s",
            request.method,
            request.url.path,
            response.status_code,
            latency_ms,
            client_ip,
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "latency_ms": round(latency_ms, 2),
                "client_ip": client_ip,
            },
        )

        return response

    # Global Exception Handlers returning clean JSON error envelopes
    @application.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        """
        Clean JSON error envelope for standard HTTP exceptions without leaking stack traces.
        """
        message = exc.detail if isinstance(exc.detail, str) else "HTTP Exception"
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.detail,
                "error": {
                    "code": exc.status_code,
                    "message": message,
                    "type": "http_error",
                },
            },
            headers=getattr(exc, "headers", None),
        )

    @application.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """
        Clean JSON error envelope for Pydantic request validation errors.
        """
        errors = exc.errors()
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": errors,
                "error": {
                    "code": 422,
                    "message": "Request validation failed",
                    "type": "validation_error",
                    "details": errors,
                },
            },
        )

    @application.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """
        Global fallback exception handler:
        Logs internal traceback server-side without leaking implementation details or secrets to clients.
        """
        logger.exception(
            "Global unhandled exception on %s %s: %s", request.method, request.url.path, exc
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "An internal server error occurred. Please try again later.",
                "error": {
                    "code": 500,
                    "message": "An internal server error occurred. Please try again later.",
                    "type": "internal_server_error",
                },
            },
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

    # Top-level metadata aliases for direct /categories & /courts access
    @application.get(
        "/categories",
        tags=["Metadata"],
        summary="List legal categories (root alias)",
        include_in_schema=False,
    )
    async def root_categories():
        from app.api.v1.judgments import list_categories
        return await list_categories()

    @application.get(
        "/courts",
        tags=["Metadata"],
        summary="List Indian courts (root alias)",
        include_in_schema=False,
    )
    async def root_courts():
        from app.api.v1.judgments import list_courts
        return await list_courts()

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
            "docs": None if is_prod else "/docs",
        }

    # Aliases for API documentation (disabled in production)
    if not is_prod:
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
