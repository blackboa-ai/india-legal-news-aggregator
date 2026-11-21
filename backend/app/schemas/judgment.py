"""
Judgment Pydantic Schemas & DTOs
India Legal News Aggregator - Free-Tier Architecture (< 250 MB RAM)
Strict Pydantic v2 validation for judgments, hybrid search results, and metadata.
"""

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Party(BaseModel):
    """Party in legal proceeding (petitioner, respondent, appellant)."""
    role: str
    name: str


def _normalize_judgment_payload(data: Any) -> Any:
    """Reusable normalizer ensuring excerpt/summary aliases and content_type defaults."""
    if isinstance(data, dict):
        if "excerpt" in data and not data.get("summary"):
            data["summary"] = data["excerpt"]
        elif "summary" in data and not data.get("excerpt"):
            data["excerpt"] = data["summary"]
        if data.get("content_type") is None:
            data["content_type"] = "unknown"
        if data.get("content_type_confidence") is None:
            data["content_type_confidence"] = 0.0
    elif hasattr(data, "excerpt"):
        if not getattr(data, "summary", None):
            try:
                setattr(data, "summary", getattr(data, "excerpt"))
            except Exception:
                pass
        if getattr(data, "content_type", None) is None:
            try:
                setattr(data, "content_type", "unknown")
            except Exception:
                pass
        if getattr(data, "content_type_confidence", None) is None:
            try:
                setattr(data, "content_type_confidence", 0.0)
            except Exception:
                pass
    return data


class JudgmentBase(BaseModel):
    """Base judgment attributes shared across schemas."""
    title: str = Field(..., description="Full title of the legal judgment")
    short_title: str | None = Field(default=None, description="Concise case name (e.g. State v. Baldev Singh)")
    court_code: str = Field(..., description="Standard court code identifier (sc, delhi-hc, etc.)")
    court_name: str = Field(..., description="Official name of the court or tribunal")
    court_level: int = Field(default=2, description="1=Supreme Court, 2=High Court, 3=Tribunal")
    judgment_date: date = Field(..., description="Date the judgment or order was pronounced")
    subject_category: str = Field(..., description="One of the 10 canonical Indian law categories")
    excerpt: str = Field(..., description="Cleaned, sanitized legal summary or headnote")
    summary: str | None = Field(default=None, description="Alias for excerpt")
    full_text: str | None = Field(default=None, description="Complete judgment body text if available")
    url: str = Field(..., description="Canonical source URL")
    parties: list[dict[str, Any]] = Field(default_factory=list, description="List of parties to the dispute")
    tags: list[str] = Field(default_factory=list, description="Statutory sections, articles, and legal tags")
    source: str = Field(..., description="Feed source origin (indiankanoon, livelaw, barandbench, sci)")
    is_archived: bool = Field(default=True, description="Whether judgment is indexed and active")
    classification_confidence: float = Field(default=0.0, description="Classification confidence score (0.0 to 1.0)")
    content_type: str = Field(default="unknown", description="Content classification: 'judgment', 'news', or 'unknown'")
    content_type_confidence: float = Field(default=0.0, description="Classification confidence score between 0.0 and 1.0")

    @model_validator(mode="before")
    @classmethod
    def populate_summary_alias(cls, data: Any) -> Any:
        return _normalize_judgment_payload(data)


class JudgmentCreate(JudgmentBase):
    """Schema for inserting a new judgment."""
    external_id: str = Field(..., description="SHA-256 hash for deduplication")


class JudgmentListItem(BaseModel):
    """Slim judgment projection for feed cards and list endpoints."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    external_id: str
    title: str
    short_title: str | None = None
    court_code: str
    court_name: str
    court_level: int = 2
    judgment_date: date
    subject_category: str
    excerpt: str
    summary: str | None = None
    url: str
    tags: list[str] = Field(default_factory=list)
    source: str = ""
    is_archived: bool = True
    classification_confidence: float = 0.0
    content_type: str = Field(default="unknown", description="Content classification: 'judgment', 'news', or 'unknown'")
    content_type_confidence: float = Field(default=0.0, description="Classification confidence score between 0.0 and 1.0")
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @model_validator(mode="before")
    @classmethod
    def populate_summary_alias(cls, data: Any) -> Any:
        return _normalize_judgment_payload(data)


class JudgmentResponse(JudgmentBase):
    """Schema for public judgment representation."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    external_id: str
    created_at: datetime
    updated_at: datetime


class JudgmentListResponse(BaseModel):
    """Paginated collection of judgments with metadata."""
    items: list[JudgmentResponse]
    total: int
    limit: int
    offset: int

    @property
    def data(self) -> list[JudgmentResponse]:
        """Backward-compatible accessor for Python callers without duplicating JSON payload."""
        return self.items


class SearchResultItem(BaseModel):
    """Ranked judgment item returned from hybrid or semantic search."""
    id: UUID
    external_id: str
    title: str
    short_title: str | None = None
    court_code: str
    court_name: str
    court_level: int = 2
    judgment_date: date
    subject_category: str
    excerpt: str
    summary: str | None = None
    full_text: str | None = None
    url: str
    parties: list[dict[str, Any]] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    source: str = ""
    is_archived: bool = True
    classification_confidence: float = 0.0
    content_type: str = Field(default="unknown", description="Content classification: 'judgment', 'news', or 'unknown'")
    content_type_confidence: float = Field(default=0.0, description="Classification confidence score between 0.0 and 1.0")
    created_at: datetime | None = None
    updated_at: datetime | None = None
    score: float = Field(..., description="Combined RRF score or similarity rank")
    keyword_rank: int | None = Field(default=None, description="1-based rank in tsvector full-text results")
    semantic_rank: int | None = Field(default=None, description="1-based rank in pgvector cosine results")

    @model_validator(mode="before")
    @classmethod
    def populate_search_summary_alias(cls, data: Any) -> Any:
        return _normalize_judgment_payload(data)


class SearchResponse(BaseModel):
    """Response contract for GET /api/v1/search and /api/v1/judgments/search."""
    results: list[SearchResultItem]
    query_type: str = Field(..., description="Execution mode: hybrid, keyword, or semantic")
    matched_terms: list[str] = Field(default_factory=list, description="Extracted legal statutes and search keywords")
    total: int = Field(..., description="Number of candidate results matching filters")


class LegalCategoryItem(BaseModel):
    """Standardized Indian legal subject domain."""
    id: str
    name: str
    description: str


class CourtItem(BaseModel):
    """Indian court code and hierarchy level."""
    code: str
    name: str
    level: int
