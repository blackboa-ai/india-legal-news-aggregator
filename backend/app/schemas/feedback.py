"""
Feedback Request and Response Schemas
India Legal News Aggregator
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FeedbackCreate(BaseModel):
    """
    Schema for submitting feedback/review.
    """
    rating: int = Field(
        ...,
        ge=1,
        le=5,
        description="Rating from 1 to 5 stars",
        examples=[5],
    )
    feedback_text: str = Field(
        ...,
        min_length=2,
        max_length=2000,
        description="User feedback comment or review text",
        examples=["The search speed and legal headnotes are super helpful!"],
    )
    email: str | None = Field(
        default=None,
        max_length=255,
        description="Optional contact email for follow-up",
        examples=["user@example.com"],
    )
    category: str = Field(
        default="general",
        max_length=50,
        description="Category: 'general', 'bug', 'feature', 'content'",
        examples=["general"],
    )


class FeedbackResponse(BaseModel):
    """
    Schema representing a saved feedback record.
    """
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    rating: int
    feedback_text: str
    email: str | None = None
    category: str = "general"
    user_id: str | None = None
    created_at: datetime


class FeedbackStats(BaseModel):
    """
    Summary metrics across user feedback submissions.
    """
    total_count: int
    average_rating: float
    rating_distribution: dict[str, int]


class FeedbackListResponse(BaseModel):
    """
    Paginated list of feedback records with overall summary stats.
    """
    data: list[FeedbackResponse]
    total: int
    stats: FeedbackStats
