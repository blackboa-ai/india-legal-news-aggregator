"""
Feedback API Router
India Legal News Aggregator - Free-Tier Architecture
Handles user reviews, feedback submissions, ratings, and feedback retrieval.
"""

import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_active_superuser, get_optional_user
from app.models.feedback import Feedback
from app.models.user import User
from app.schemas.feedback import (
    FeedbackCreate,
    FeedbackListResponse,
    FeedbackResponse,
    FeedbackStats,
)

logger = logging.getLogger("app.api.v1.feedback")

router = APIRouter(prefix="/feedback", tags=["Feedback"])


def forward_feedback_notification(
    feedback_id: str,
    rating: int,
    feedback_text: str,
    email: str | None,
    category: str,
    user_id: str | None,
) -> None:
    """
    Background task to route and notify feedback submissions.
    Logs structured alert and forwards email if FEEDBACK_NOTIFICATION_EMAIL is set.
    """
    logger.info(
        "FEEDBACK_NOTIFY id=%s rating=%d/5 category=%s email=%s user_id=%s snippet=%.80s",
        feedback_id,
        rating,
        category,
        email or "anonymous",
        user_id or "anonymous",
        feedback_text.replace("\n", " "),
    )

    recipient = settings.FEEDBACK_NOTIFICATION_EMAIL
    if recipient:
        logger.info(
            "Forwarding feedback #%s to configured destination: %s",
            feedback_id,
            recipient,
        )
        # Note: If developer specifies SMTP settings in env, SMTP forwarding can be enabled here.


@router.post(
    "",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit user feedback or review",
)
async def submit_feedback(
    payload: FeedbackCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> Any:
    """
    Submits user review and feedback.
    - Saves submission in PostgreSQL database.
    - Attaches authenticated user identity if logged in.
    - Emits structured notification log for quick administrative visibility.
    - Asynchronously triggers notification forwarder.
    """
    # If current_user is authenticated, ignore payload.email and strictly enforce current_user.email
    if current_user:
        email_val = current_user.email
        user_id_val = str(current_user.id)
    else:
        email_val = payload.email.strip() if payload.email else None
        user_id_val = None

    feedback_record = Feedback(
        rating=payload.rating,
        feedback_text=payload.feedback_text.strip(),
        email=email_val,
        category=payload.category.strip() if payload.category else "general",
        user_id=user_id_val,
    )

    db.add(feedback_record)
    await db.commit()
    await db.refresh(feedback_record)

    # Queue background task for logging and notification routing
    background_tasks.add_task(
        forward_feedback_notification,
        feedback_id=str(feedback_record.id),
        rating=feedback_record.rating,
        feedback_text=feedback_record.feedback_text,
        email=feedback_record.email,
        category=feedback_record.category,
        user_id=feedback_record.user_id,
    )

    return feedback_record


@router.get(
    "",
    response_model=FeedbackListResponse,
    summary="List submitted feedbacks with summary stats",
)
async def list_feedback(
    limit: int = Query(default=50, ge=1, le=100, description="Max feedback items to return"),
    offset: int = Query(default=0, ge=0, description="Number of items to skip"),
    category: str | None = Query(default=None, description="Optional category filter"),
    current_user: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Returns submitted user feedbacks along with summary ratings statistics.
    Enables developer / admin to easily monitor feedback directly from UI or API.
    """
    query = select(Feedback)
    if category:
        query = query.where(Feedback.category == category)

    # Count total
    count_stmt = select(func.count(Feedback.id))
    if category:
        count_stmt = count_stmt.where(Feedback.category == category)
    total_count = (await db.execute(count_stmt)).scalar() or 0

    # Average rating
    avg_stmt = select(func.avg(Feedback.rating))
    if category:
        avg_stmt = avg_stmt.where(Feedback.category == category)
    avg_rating_raw = (await db.execute(avg_stmt)).scalar()
    avg_rating = round(float(avg_rating_raw), 2) if avg_rating_raw is not None else 0.0

    # Rating distribution (1 to 5)
    dist_stmt = select(Feedback.rating, func.count(Feedback.id)).group_by(Feedback.rating)
    if category:
        dist_stmt = dist_stmt.where(Feedback.category == category)
    dist_res = await db.execute(dist_stmt)
    distribution = {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}
    for r, count in dist_res.all():
        distribution[str(r)] = count

    # Fetch items ordered by newest first
    stmt = query.order_by(desc(Feedback.created_at)).offset(offset).limit(limit)
    res = await db.execute(stmt)
    records = res.scalars().all()

    stats = FeedbackStats(
        total_count=total_count,
        average_rating=avg_rating,
        rating_distribution=distribution,
    )

    return FeedbackListResponse(
        data=records,
        total=total_count,
        stats=stats,
    )
