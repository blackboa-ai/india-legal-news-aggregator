"""
API v1 Router Aggregator
Mounts all v1 sub-routers.
"""

from fastapi import APIRouter

from app.api.v1 import health, judgments

api_router = APIRouter()

# Include health router -> results in /api/v1/health
api_router.include_router(health.router, tags=["Health"])

# Include judgments & search router -> results in /api/v1/judgments, /api/v1/search, etc.
api_router.include_router(judgments.router, tags=["Judgments & Search"])
