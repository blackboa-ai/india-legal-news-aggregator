"""
Schemas module alias re-exporting Pydantic models from app.schemas.
Maintains compatibility with both app.schemas and app.schemas.judgment imports.
"""

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

__all__ = [
    "HealthResponse",
    "Party",
    "JudgmentBase",
    "JudgmentCreate",
    "JudgmentResponse",
    "JudgmentListResponse",
    "SearchResultItem",
    "SearchResponse",
    "LegalCategoryItem",
    "CourtItem",
]
