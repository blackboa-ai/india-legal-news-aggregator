"""
Judgment Pydantic Schemas & DTOs
India Legal News Aggregator - Free-Tier Architecture (< 250 MB RAM)
Strict Pydantic v2 validation for judgments, hybrid search results, and metadata.
"""

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Party(BaseModel):
    """Party in legal proceeding (petitioner, respondent, appellant)."""
    role: str
    name: str


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
    full_text: str | None = Field(default=None, description="Complete judgment body text if available")
    url: str = Field(..., description="Canonical source URL")
    parties: list[dict[str, Any]] = Field(default_factory=list, description="List of parties to the dispute")
    tags: list[str] = Field(default_factory=list, description="Statutory sections, articles, and legal tags")
    source: str = Field(..., description="Feed source origin (indiankanoon, livelaw, barandbench, sci)")
    is_archived: bool = Field(default=True, description="Whether judgment is indexed and active")
    classification_confidence: float = Field(default=0.0, description="Classification confidence score (0.0 to 1.0)")


class JudgmentCreate(JudgmentBase):
    """Schema for inserting a new judgment."""
    external_id: str = Field(..., description="SHA-256 hash for deduplication")


class JudgmentResponse(JudgmentBase):
    """Schema for public judgment representation."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    external_id: str
    created_at: datetime
    updated_at: datetime


class JudgmentListResponse(BaseModel):
    """Paginated collection of judgments with metadata."""
    data: list[JudgmentResponse]
    total: int
    limit: int
    offset: int


class SearchResultItem(BaseModel):
    """Ranked judgment item returned from hybrid or semantic search."""
    id: UUID
    external_id: str
    title: str
    short_title: str | None = None
    court_code: str
    court_name: str
    court_level: int
    judgment_date: date
    subject_category: str
    excerpt: str
    full_text: str | None = None
    url: str
    parties: list[dict[str, Any]] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    source: str = ""
    is_archived: bool = True
    classification_confidence: float = 0.0
    created_at: datetime | None = None
    updated_at: datetime | None = None
    score: float = Field(..., description="Combined RRF score or similarity rank")
    keyword_rank: int | None = Field(default=None, description="1-based rank in tsvector full-text results")
    semantic_rank: int | None = Field(default=None, description="1-based rank in pgvector cosine results")


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
