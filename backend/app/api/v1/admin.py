"""
Admin API Router
India Legal News Aggregator - Free-Tier Architecture (< 250 MB RAM)
Provides:
- POST /admin/refresh (Triggers immediate asynchronous RSS ingestion cycle)
"""

import asyncio
import hmac
import logging

from fastapi import APIRouter, Header, HTTPException, status

from app.core.config import settings
from app.workers.ingestion_worker import ingestion_worker

logger = logging.getLogger("app.api.v1.admin")

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.post(
    "/refresh",
    summary="Trigger immediate asynchronous RSS ingestion cycle",
)
async def refresh_feeds(
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
):
    """
    Administrative trigger to run legal RSS feed fetching and deduplication cycle.
    Protected by ADMIN_API_KEY secret.
    """
    if not x_admin_key or not hmac.compare_digest(x_admin_key, settings.ADMIN_API_KEY):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing X-Admin-Key header",
        )

    # Fire background task without blocking request, store task reference and attach done callback
    task = asyncio.create_task(ingestion_worker.run_once())
    task.add_done_callback(lambda t: logger.error(t.exception()) if not t.cancelled() and t.exception() else None)

    return {
        "status": "triggered",
        "message": "Asynchronous legal RSS ingestion initiated successfully",
    }
