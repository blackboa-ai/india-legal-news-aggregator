"""
User Topics & Research Folders API Router
India Legal News Aggregator - Free-Tier Architecture (< 250 MB RAM)
Provides:
- GET /topics (List research folders)
- POST /topics (Create new research folder)
- POST /topics/{topic_id}/judgments (Add judgment to topic folder)
- DELETE /topics/{topic_id} (Remove research folder)
"""

import logging
import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.judgment import Judgment
from app.models.topic import Topic, TopicJudgment
from app.models.user import User
from app.schemas.user_features import (
    AddJudgmentToTopicRequest,
    TopicCreateRequest,
    TopicListResponse,
    TopicResponse,
)

logger = logging.getLogger("app.api.v1.user")

router = APIRouter(prefix="/topics", tags=["Topics"])


@router.get(
    "",
    response_model=TopicListResponse,
    summary="List user custom research topic folders",
)
async def list_topics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns research topic folders created by the current user.
    """
    uid_str = str(current_user.id)

    # Subquery for judgment count per topic
    count_subq = (
        select(TopicJudgment.topic_id, func.count(TopicJudgment.judgment_id).label("j_count"))
        .group_by(TopicJudgment.topic_id)
        .subquery()
    )

    stmt = (
        select(Topic, func.coalesce(count_subq.c.j_count, 0).label("count"))
        .outerjoin(count_subq, Topic.id == count_subq.c.topic_id)
        .where(Topic.user_id == uid_str)
        .order_by(Topic.created_at.desc())
    )
    res = await db.execute(stmt)
    rows = res.all()

    items = [
        TopicResponse(
            id=topic.id,
            user_id=topic.user_id,
            name=topic.name,
            description=topic.description,
            created_at=topic.created_at,
            judgment_count=count,
        )
        for topic, count in rows
    ]

    return TopicListResponse(data=items, total=len(items))


@router.post(
    "",
    response_model=TopicResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a custom legal research folder / topic",
)
async def create_topic(
    payload: TopicCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Creates a new research topic folder (e.g. 'Anticipatory Bail Precedents').
    """
    uid_str = str(current_user.id)
    topic = Topic(
        id=uuid.uuid4(),
        user_id=uid_str,
        name=payload.name.strip(),
        description=payload.description.strip() if payload.description else None,
    )
    db.add(topic)
    await db.commit()
    await db.refresh(topic)

    return TopicResponse(
        id=topic.id,
        user_id=topic.user_id,
        name=topic.name,
        description=topic.description,
        created_at=topic.created_at,
        judgment_count=0,
    )


@router.post(
    "/{topic_id}/judgments",
    summary="Associate a judgment with a research topic folder",
)
async def add_judgment_to_topic(
    topic_id: UUID,
    payload: AddJudgmentToTopicRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Links a judgment to a research topic folder.
    """
    uid_str = str(current_user.id)

    # Verify topic exists and belongs to user
    t_stmt = select(Topic).where(Topic.id == topic_id, Topic.user_id == uid_str)
    t_res = await db.execute(t_stmt)
    topic = t_res.scalar_one_or_none()
    if not topic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Topic folder not found",
        )

    # Verify judgment exists
    j_stmt = select(Judgment).where(Judgment.id == payload.judgment_id)
    j_res = await db.execute(j_stmt)
    judgment = j_res.scalar_one_or_none()
    if not judgment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Judgment not found",
        )

    # Check if already added
    assoc_stmt = select(TopicJudgment).where(
        TopicJudgment.topic_id == topic_id,
        TopicJudgment.judgment_id == payload.judgment_id,
    )
    assoc_res = await db.execute(assoc_stmt)
    if assoc_res.scalar_one_or_none():
        return {
            "status": "already_added",
            "topic_id": str(topic_id),
            "judgment_id": str(payload.judgment_id),
        }

    assoc = TopicJudgment(topic_id=topic_id, judgment_id=payload.judgment_id)
    db.add(assoc)
    await db.commit()

    return {
        "status": "success",
        "topic_id": str(topic_id),
        "judgment_id": str(payload.judgment_id),
    }


@router.delete(
    "/{topic_id}",
    summary="Delete a research topic folder",
)
async def delete_topic(
    topic_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Deletes a research topic folder.
    """
    uid_str = str(current_user.id)

    t_stmt = select(Topic).where(Topic.id == topic_id, Topic.user_id == uid_str)
    t_res = await db.execute(t_stmt)
    topic = t_res.scalar_one_or_none()
    if not topic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Topic folder not found",
        )

    await db.delete(topic)
    await db.commit()

    return {
        "status": "deleted",
        "topic_id": str(topic_id),
    }
