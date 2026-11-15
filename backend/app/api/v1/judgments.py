"""
Judgments & Hybrid Search API Router
India Legal News Aggregator - Free-Tier Architecture (< 250 MB RAM)

Provides:
- GET /judgments (paginated feed with Redis 300s cache + in-memory fallback)
- GET /judgments/search & /search (hybrid BM25 + pgvector RRF search)
- GET /judgments/{id} (full judgment detail view)
- GET /similar/{id} (top-5 related precedents via cosine distance)
- GET /categories & /courts (canonical Indian legal domain metadata)
"""

import logging
from datetime import date
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.judgment import Judgment
from app.schemas.judgment import (
    CourtItem,
    JudgmentListResponse,
    JudgmentResponse,
    LegalCategoryItem,
    SearchResponse,
    SearchResultItem,
)
from app.services.cache_service import cache_service
from app.services.legal_classifier import CANONICAL_CATEGORIES
from app.services.search_service import search_service

logger = logging.getLogger("app.api.judgments")

router = APIRouter()

# ------------------------------------------------------------------------------
# Canonical Indian Legal Metadata
# ------------------------------------------------------------------------------
CATEGORY_DESCRIPTIONS = {
    "Constitutional": "Fundamental rights, writ petitions, judicial review, and basic structure doctrine",
    "Criminal": "Offences under IPC/BNS, bail under CrPC/BNSS, police investigations, and criminal trials",
    "Civil": "Property disputes, contracts, injunctions, and civil procedures under CPC",
    "Corporate": "Insolvency and bankruptcy (IBC), company law, SEBI regulations, and mergers",
    "Administrative": "Service law, government appointments, disciplinary proceedings, and statutory bodies",
    "Human Rights": "Custodial violence, illegal detention, prisoner welfare, and civil liberties",
    "Environment": "Pollution control, forest conservation, NGT directions, and ecological protection",
    "Labour": "Industrial disputes, wage regulations, trade unions, gratuity, and retrenchment",
    "Family": "Marriage, divorce, maintenance under 125 CrPC, child custody, and succession",
    "Education": "Examinations, seat allocations, university admissions, and regulatory standards",
}

INDIAN_COURTS: list[dict[str, Any]] = [
    {"code": "sc", "name": "Supreme Court of India", "level": 1},
    {"code": "delhi-hc", "name": "High Court of Delhi", "level": 2},
    {"code": "bombay-hc", "name": "High Court of Bombay", "level": 2},
    {"code": "madras-hc", "name": "High Court of Madras", "level": 2},
    {"code": "calcutta-hc", "name": "High Court of Calcutta", "level": 2},
    {"code": "allahabad-hc", "name": "High Court of Allahabad", "level": 2},
    {"code": "karnataka-hc", "name": "High Court of Karnataka", "level": 2},
    {"code": "kerala-hc", "name": "High Court of Kerala", "level": 2},
    {"code": "punjab-haryana-hc", "name": "High Court of Punjab and Haryana", "level": 2},
    {"code": "gujarat-hc", "name": "High Court of Gujarat", "level": 2},
    {"code": "nclat", "name": "National Company Law Appellate Tribunal", "level": 3},
    {"code": "ngt", "name": "National Green Tribunal", "level": 3},
]


# ------------------------------------------------------------------------------
# 1. Paginated Judgments Feed (Redis Cached 300s)
# ------------------------------------------------------------------------------
@router.get(
    "/judgments",
    response_model=JudgmentListResponse,
    summary="Get paginated judgments feed with filters and Redis caching",
)
async def list_judgments(
    category: str | None = Query(default=None, description="Filter by legal subject domain"),
    court: str | None = Query(default=None, description="Filter by court identifier code"),
    date_from: date | None = Query(default=None, description="Filter judgments on or after this date"),
    date_to: date | None = Query(default=None, description="Filter judgments on or before this date"),
    limit: int = Query(default=20, ge=1, le=100, description="Page size limit"),
    offset: int = Query(default=0, ge=0, description="Offset cursor for pagination"),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns a paginated list of judgments with multi-dimensional filtering.
    Cached in Redis / in-memory for 300 seconds to minimize database load.
    """
    cache_key = f"judgments:feed:{category}:{court}:{date_from}:{date_to}:{limit}:{offset}"

    # 1. Attempt cache lookup
    cached_data = await cache_service.get_json(cache_key)
    if cached_data:
        return JudgmentListResponse(**cached_data)

    # 2. Build SQLAlchemy query with filters
    base_conditions = [Judgment.is_archived.is_(True)]
    if category:
        base_conditions.append(Judgment.subject_category == category.strip())
    if court:
        base_conditions.append(Judgment.court_code == court.strip().lower())
    if date_from:
        base_conditions.append(Judgment.judgment_date >= date_from)
    if date_to:
        base_conditions.append(Judgment.judgment_date <= date_to)

    # Count total matching rows
    count_stmt = select(func.count()).select_from(Judgment).where(*base_conditions)
    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one_or_none() or 0

    # Fetch page items
    stmt = (
        select(Judgment)
        .where(*base_conditions)
        .order_by(Judgment.judgment_date.desc(), Judgment.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(stmt)
    judgments = result.scalars().all()

    # Convert to response DTOs
    serialized_data = [JudgmentResponse.model_validate(j) for j in judgments]
    response_payload = JudgmentListResponse(
        data=serialized_data,
        total=total,
        limit=limit,
        offset=offset,
    )

    # 3. Cache response in Redis for 300s (graceful fallback if Redis is offline)
    await cache_service.set_json(cache_key, response_payload.model_dump(mode="json"), ttl_seconds=300)

    return response_payload


# ------------------------------------------------------------------------------
# 2. Hybrid RRF Search Endpoints
# ------------------------------------------------------------------------------
@router.get(
    "/judgments/search",
    response_model=SearchResponse,
    summary="Hybrid legal search (BM25 + pgvector RRF)",
)
@router.get(
    "/search",
    response_model=SearchResponse,
    summary="Hybrid legal search (BM25 + pgvector RRF)",
    include_in_schema=True,
)
async def search_judgments(
    q: str = Query(..., min_length=1, description="Legal search query, statute, or citation"),
    mode: str = Query(default="hybrid", description="Search mode: hybrid, keyword, or semantic"),
    category: str | None = Query(default=None, description="Filter by legal subject domain"),
    court: str | None = Query(default=None, description="Filter by court identifier code"),
    limit: int = Query(default=10, ge=1, le=50, description="Max results to return"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
    db: AsyncSession = Depends(get_db),
):
    """
    Executes Reciprocal Rank Fusion (RRF, k=60) combining PostgreSQL tsvector GIN
    BM25 ranking and pgvector cosine distance.
    """
    search_exec_result = await search_service.search(
        session=db,
        query=q,
        mode=mode,
        category=category,
        court=court,
        limit=limit,
        offset=offset,
    )

    items = [
        SearchResultItem(
            id=c.id,
            external_id=c.external_id,
            title=c.title,
            short_title=c.short_title,
            court_code=c.court_code,
            court_name=c.court_name,
            court_level=c.court_level,
            judgment_date=c.judgment_date,
            subject_category=c.subject_category,
            excerpt=c.excerpt,
            url=c.url,
            tags=c.tags,
            source=c.source,
            score=c.score,
            keyword_rank=c.keyword_rank,
            semantic_rank=c.semantic_rank,
        )
        for c in search_exec_result.results
    ]

    return SearchResponse(
        results=items,
        query_type=search_exec_result.query_type,
        matched_terms=search_exec_result.matched_terms,
        total=search_exec_result.total,
    )


# ------------------------------------------------------------------------------
# 3. Judgment Detail View
# ------------------------------------------------------------------------------
@router.get(
    "/judgments/{id}",
    response_model=JudgmentResponse,
    summary="Get full judgment details by ID",
)
async def get_judgment_by_id(
    id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Returns full judgment metadata, parties, statutory tags, excerpt, and full text.
    """
    stmt = select(Judgment).where(Judgment.id == id, Judgment.is_archived.is_(True))
    result = await db.execute(stmt)
    judgment = result.scalar_one_or_none()

    if not judgment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Judgment with ID '{id}' was not found.",
        )

    return JudgmentResponse.model_validate(judgment)


# ------------------------------------------------------------------------------
# 4. Similar Precedents Retrieval
# ------------------------------------------------------------------------------
@router.get(
    "/similar/{id}",
    response_model=list[JudgmentResponse],
    summary="Find related precedents via pgvector cosine distance",
)
@router.get(
    "/judgments/{id}/similar",
    response_model=list[JudgmentResponse],
    summary="Find related precedents via pgvector cosine distance",
)
async def get_similar_judgments(
    id: UUID,
    limit: int = Query(default=5, ge=1, le=20, description="Max similar judgments to return"),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves top 5 related legal precedents via pgvector cosine similarity
    (ORDER BY embedding <=> target.embedding LIMIT 5).
    """
    similar = await search_service.find_similar_judgments(db, id, limit=limit)
    return [JudgmentResponse.model_validate(j) for j in similar]


# ------------------------------------------------------------------------------
# 5. Categories and Courts Metadata
# ------------------------------------------------------------------------------
@router.get(
    "/categories",
    response_model=list[LegalCategoryItem],
    summary="List the 10 canonical Indian legal categories",
)
async def list_categories():
    """
    Returns the standardized 10 Indian legal categories.
    """
    return [
        LegalCategoryItem(
            id=cat.lower().replace(" ", "-"),
            name=cat,
            description=CATEGORY_DESCRIPTIONS.get(cat, f"Legal judgments in {cat}"),
        )
        for cat in CANONICAL_CATEGORIES
    ]


@router.get(
    "/courts",
    response_model=list[CourtItem],
    summary="List Indian courts and tribunals",
)
async def list_courts():
    """
    Returns supported Indian courts and judicial bodies with hierarchy levels.
    """
    return [CourtItem(**court) for court in INDIAN_COURTS]
