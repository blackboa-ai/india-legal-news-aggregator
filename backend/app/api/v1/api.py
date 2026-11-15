"""
API v1 Router Aggregator
Mounts all v1 sub-routers.
"""

from fastapi import APIRouter

from app.api.v1 import health

api_router = APIRouter()

# Include health router -> results in /api/v1/health when api_router is mounted under /api/v1
api_router.include_router(health.router, tags=["Health"])
