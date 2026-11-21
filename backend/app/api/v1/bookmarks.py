"""
Bookmarks & Personalized Alerts API Router
India Legal News Aggregator - Free-Tier Architecture (< 250 MB RAM)
Provides:
- GET /bookmarks (List user bookmarks with attached judgments)
- POST /bookmarks/{judgment_id} (Bookmark a judgment with optional notes/tags, duplicate prevention)
- DELETE /bookmarks/{judgment_id} (Remove judgment from bookmarks)
- GET /alerts (List user-configured legal alerts)
- POST /alerts (Create a new legal domain, court, or statutory keyword alert)
- DELETE /alerts/{alert_id} (Delete an alert)
- GET /alerts/matches (Find recent judgments matching active user alerts)
"""

import logging
import uuid
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.alert import Alert
from app.models.bookmark import Bookmark
from app.models.judgment import Judgment
from app.models.user import User
from app.schemas.judgment import JudgmentResponse
from app.schemas.user_features import (
    AlertCreateRequest,
    AlertListResponse,
    AlertMatchesResponse,
    AlertResponse,
    BookmarkCreate,
    BookmarkCreateRequest,
    BookmarkListResponse,
    BookmarkResponse,
)
from app.services.alert_service import alert_service

logger = logging.getLogger("app.api.v1.bookmarks")

bookmarks_router = APIRouter(prefix="/bookmarks", tags=["Bookmarks"])
alerts_router = APIRouter(prefix="/alerts", tags=["Alerts"])


# ==============================================================================
# 1. Bookmarks Endpoints
# ==============================================================================
@bookmarks_router.get(
    "",
    response_model=BookmarkListResponse,
    summary="Get paginated list of user bookmarks with full judgment metadata",
)
async def list_bookmarks(
    limit: int = Query(default=20, ge=1, le=100, description="Page limit"),
    offset: int = Query(default=0, ge=0, description="Page offset"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves all judgments saved by the authenticated user.
    """
    uid = current_user.id

    # 1. Count total bookmarks
    count_stmt = select(func.count(Bookmark.id)).where(Bookmark.user_id == uid)
    count_res = await db.execute(count_stmt)
    total = count_res.scalar() or 0

    # 2. Query bookmarks with joined judgments
    stmt = (
        select(Bookmark)
        .where(Bookmark.user_id == uid)
        .options(selectinload(Bookmark.judgment))
        .order_by(Bookmark.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    res = await db.execute(stmt)
    bookmarks = res.scalars().all()

    items = []
    for b in bookmarks:
        j_resp = JudgmentResponse.model_validate(b.judgment) if b.judgment else None
        items.append(
            BookmarkResponse(
                id=b.id,
                user_id=b.user_id,
                judgment_id=b.judgment_id,
                notes=b.notes,
                tags=b.tags or [],
                created_at=b.created_at,
                judgment=j_resp,
            )
        )

    return BookmarkListResponse(
        data=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@bookmarks_router.post(
    "/{judgment_id}",
    response_model=BookmarkResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Bookmark a judgment with optional research notes and custom tags",
)
async def create_bookmark_by_id(
    judgment_id: UUID,
    payload: BookmarkCreateRequest | None = Body(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Saves a judgment to the user's bookmarks.
    Enforces duplicate prevention: raises 409 Conflict if already bookmarked.
    """
    uid = current_user.id

    # 1. Verify judgment exists
    j_stmt = select(Judgment).where(Judgment.id == judgment_id)
    j_res = await db.execute(j_stmt)
    judgment = j_res.scalar_one_or_none()
    if not judgment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Judgment not found",
        )

    # 2. Check for duplicate bookmark
    dup_stmt = select(Bookmark).where(
        Bookmark.user_id == uid,
        Bookmark.judgment_id == judgment_id,
    )
    dup_res = await db.execute(dup_stmt)
    if dup_res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Judgment is already bookmarked by user",
        )

    # 3. Create bookmark
    notes = payload.notes if payload else None
    tags = payload.tags if payload else []

    bookmark = Bookmark(
        id=uuid.uuid4(),
        user_id=uid,
        judgment_id=judgment_id,
        notes=notes,
        tags=tags,
        created_at=datetime.now(UTC),
    )
    db.add(bookmark)
    await db.commit()
    await db.refresh(bookmark)

    return BookmarkResponse(
        id=bookmark.id,
        user_id=bookmark.user_id,
        judgment_id=bookmark.judgment_id,
        notes=bookmark.notes,
        tags=bookmark.tags or [],
        created_at=bookmark.created_at,
        judgment=JudgmentResponse.model_validate(judgment),
    )


@bookmarks_router.post(
    "",
    response_model=BookmarkResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Save a bookmark using request body payload",
)
async def create_bookmark_body(
    payload: BookmarkCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Alternative endpoint to bookmark a judgment with JSON body containing judgment_id.
    """
    return await create_bookmark_by_id(
        judgment_id=payload.judgment_id,
        payload=BookmarkCreateRequest(notes=payload.notes, tags=payload.tags),
        current_user=current_user,
        db=db,
    )


@bookmarks_router.delete(
    "/{judgment_id}",
    summary="Remove a judgment from user's bookmarks",
)
async def delete_bookmark(
    judgment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Deletes a bookmarked judgment for the authenticated user.
    """
    uid = current_user.id

    stmt = select(Bookmark).where(
        Bookmark.user_id == uid,
        Bookmark.judgment_id == judgment_id,
    )
    res = await db.execute(stmt)
    bookmark = res.scalar_one_or_none()

    if not bookmark:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bookmark not found",
        )

    await db.delete(bookmark)
    await db.commit()

    return {
        "status": "deleted",
        "judgment_id": str(judgment_id),
    }


# ==============================================================================
# 2. Topic & Statute Alerts Endpoints
# ==============================================================================
@alerts_router.get(
    "",
    response_model=AlertListResponse,
    summary="List all legal domain, court, and statute alerts for the current user",
)
async def list_alerts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves all alerts created by the authenticated user.
    """
    uid = current_user.id
    stmt = select(Alert).where(Alert.user_id == uid).order_by(Alert.created_at.desc())
    res = await db.execute(stmt)
    alerts = res.scalars().all()

    return AlertListResponse(
        data=[AlertResponse.model_validate(a) for a in alerts],
        total=len(alerts),
    )


@alerts_router.post(
    "",
    response_model=AlertResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new alert for legal domains, courts, or statutory sections",
)
async def create_alert(
    payload: AlertCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Subscribes the user to personalized notifications for legal domains (e.g. Criminal),
    courts (e.g. sc), or statutory sections/keywords (e.g. ['Section 438', 'IBC']).
    """
    uid = current_user.id

    now = datetime.now(UTC)
    alert = Alert(
        id=uuid.uuid4(),
        user_id=uid,
        title=payload.title.strip(),
        category=payload.category.strip() if payload.category else None,
        court_code=payload.court_code.strip() if payload.court_code else None,
        keywords=[kw.strip() for kw in payload.keywords if kw.strip()],
        query=payload.query.strip() if payload.query else None,
        is_active=payload.is_active,
        created_at=now,
        updated_at=now,
    )
    db.add(alert)
    await db.commit()
    await db.refresh(alert)

    return AlertResponse.model_validate(alert)


@alerts_router.delete(
    "/{alert_id}",
    summary="Delete an alert subscription",
)
async def delete_alert(
    alert_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Removes an alert subscription owned by the authenticated user.
    """
    uid = current_user.id

    stmt = select(Alert).where(Alert.id == alert_id, Alert.user_id == uid)
    res = await db.execute(stmt)
    alert = res.scalar_one_or_none()

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found",
        )

    await db.delete(alert)
    await db.commit()

    return {
        "status": "deleted",
        "alert_id": str(alert_id),
    }


@alerts_router.get(
    "/matches",
    response_model=AlertMatchesResponse,
    summary="Get recent judgments matching current user's active alerts",
)
async def get_alert_matches(
    alert_id: UUID | None = Query(default=None, description="Optional alert ID to scope matches"),
    limit: int = Query(default=20, ge=1, le=100, description="Max matches to return"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Scans recent legal judgments against the user's active alert rules.
    Returns matched judgments with highlighting of which statutory sections/keywords matched.
    """
    uid = current_user.id
    alert_id_val = alert_id if isinstance(alert_id, UUID) else None
    limit_val = limit if isinstance(limit, int) else 20

    matches = await alert_service.find_matches_for_user(
        db=db,
        user_id=uid,
        alert_id=alert_id_val,
        limit=limit_val,
    )

    return AlertMatchesResponse(
        matches=matches,
        total=len(matches),
    )


# Combined router for easy mounting
router = APIRouter()
router.include_router(bookmarks_router)
router.include_router(alerts_router)
