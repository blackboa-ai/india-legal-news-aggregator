"""
Schemas Package
Exports all Pydantic v2 DTOs and request/response models.
"""

from app.schemas.auth import (
    GoogleAuthRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from app.schemas.health import HealthResponse
from app.schemas.judgment import (
    CourtItem,
    JudgmentBase,
    JudgmentCreate,
    JudgmentListResponse,
    JudgmentResponse,
    LegalCategoryItem,
    Party,
    SearchResponse,
    SearchResultItem,
)
from app.schemas.user_features import (
    AddJudgmentToTopicRequest,
    AlertCreateRequest,
    AlertListResponse,
    AlertMatchesResponse,
    AlertMatchItem,
    AlertResponse,
    BookmarkCreate,
    BookmarkCreateRequest,
    BookmarkListResponse,
    BookmarkResponse,
    TopicCreateRequest,
    TopicListResponse,
    TopicResponse,
)

__all__ = [
    # Health
    "HealthResponse",
    # Judgments & Search
    "Party",
    "JudgmentBase",
    "JudgmentCreate",
    "JudgmentResponse",
    "JudgmentListResponse",
    "SearchResultItem",
    "SearchResponse",
    "LegalCategoryItem",
    "CourtItem",
    # Auth
    "UserRegisterRequest",
    "UserLoginRequest",
    "GoogleAuthRequest",
    "RefreshTokenRequest",
    "TokenResponse",
    "UserResponse",
    # User features (Bookmarks, Alerts, Topics)
    "BookmarkCreateRequest",
    "BookmarkCreate",
    "BookmarkResponse",
    "BookmarkListResponse",
    "AlertCreateRequest",
    "AlertResponse",
    "AlertListResponse",
    "AlertMatchItem",
    "AlertMatchesResponse",
    "TopicCreateRequest",
    "AddJudgmentToTopicRequest",
    "TopicResponse",
    "TopicListResponse",
]
