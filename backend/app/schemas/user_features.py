"""
User Features Pydantic Schemas & DTOs
India Legal News Aggregator - Free-Tier Architecture (< 250 MB RAM)
Strict Pydantic v2 validation for Bookmarks, Personalized Alerts, and Research Topics.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.judgment import JudgmentResponse


# ------------------------------------------------------------------------------
# Bookmarks Schemas
# ------------------------------------------------------------------------------
class BookmarkCreateRequest(BaseModel):
    """Optional payload for POST /api/v1/bookmarks/{judgment_id}."""
    notes: str | None = Field(default=None, description="Optional private research notes or summary")
    tags: list[str] = Field(default_factory=list, description="Custom organizational tags (e.g. ['anticipatory-bail', 'client-a'])")


class BookmarkCreate(BookmarkCreateRequest):
    """Payload for POST /api/v1/bookmarks when judgment_id is in request body."""
    judgment_id: UUID = Field(..., description="Target judgment unique identifier")


class BookmarkResponse(BaseModel):
    """Representation of a saved legal bookmark."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: str
    judgment_id: UUID
    notes: str | None = None
    tags: list[str] = Field(default_factory=list)
    created_at: datetime
    judgment: JudgmentResponse | None = Field(default=None, description="Attached judgment details if loaded")


class BookmarkListResponse(BaseModel):
    """Paginated collection of bookmarked judgments."""
    data: list[BookmarkResponse]
    total: int
    limit: int
    offset: int


# ------------------------------------------------------------------------------
# Topic & Statute Alerts Schemas
# ------------------------------------------------------------------------------
class AlertCreateRequest(BaseModel):
    """Payload for creating a personalized legal alert."""
    title: str = Field(..., min_length=1, max_length=200, description="User-defined label for the alert")
    category: str | None = Field(default=None, description="Legal subject domain filter (e.g. Criminal, Corporate)")
    court_code: str | None = Field(default=None, description="Court code filter (e.g. sc, delhi-hc)")
    keywords: list[str] = Field(
        default_factory=list,
        description="Statutory sections or legal keywords (e.g. ['Section 438', 'IBC', 'Article 21'])",
    )
    query: str | None = Field(default=None, description="Optional free-text search query")
    is_active: bool = Field(default=True, description="Whether alert actively checks new judgments")


class AlertResponse(BaseModel):
    """Representation of an active or inactive legal alert."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: str
    title: str
    category: str | None = None
    court_code: str | None = None
    keywords: list[str] = Field(default_factory=list)
    query: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class AlertListResponse(BaseModel):
    """Collection of user-configured alerts."""
    data: list[AlertResponse]
    total: int


class AlertMatchItem(BaseModel):
    """A recent judgment matching an active alert rule."""
    alert_id: UUID
    alert_title: str
    matched_keywords: list[str] = Field(default_factory=list, description="Specific statutory or keyword matches")
    judgment: JudgmentResponse


class AlertMatchesResponse(BaseModel):
    """List of recent matching judgments across user's active alerts."""
    matches: list[AlertMatchItem]
    total: int


# ------------------------------------------------------------------------------
# Research Topics (Folders) Schemas
# ------------------------------------------------------------------------------
class TopicCreateRequest(BaseModel):
    """Payload for creating a custom research topic/folder."""
    name: str = Field(..., min_length=1, max_length=200, description="Folder or topic title")
    description: str | None = Field(default=None, description="Detailed brief or scope of the research folder")


class AddJudgmentToTopicRequest(BaseModel):
    """Payload for adding a judgment to a topic folder."""
    judgment_id: UUID


class TopicResponse(BaseModel):
    """Representation of a research topic/folder."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: str
    name: str
    description: str | None = None
    created_at: datetime
    judgment_count: int = Field(default=0, description="Number of judgments saved in this topic")


class TopicListResponse(BaseModel):
    """Collection of user research topic folders."""
    data: list[TopicResponse]
    total: int
