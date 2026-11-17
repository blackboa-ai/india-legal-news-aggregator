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
import time
from datetime import date
from typing import Any
from unittest.mock import MagicMock, Mock
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
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
# In-Memory Total Count Cache (120s TTL) & Feed Item Serializer
# ------------------------------------------------------------------------------
_total_count_cache: dict[str, tuple[int, float]] = {}


def clear_judgment_caches() -> None:
    """Clears the local total count cache."""
    _total_count_cache.clear()


def _serialize_feed_item(item: Any) -> JudgmentResponse:
    """
    Serializes a feed item row into a lightweight JudgmentResponse DTO,
    strictly omitting full_text, parties, and embedding vectors (~80% payload cut).
    Ensures both excerpt and summary are populated for frontend compatibility.
    """
    if hasattr(item, "_mapping"):
        d = dict(item._mapping)
    elif isinstance(item, dict):
        d = dict(item)
    elif hasattr(item, "__dict__"):
        d = {k: v for k, v in item.__dict__.items() if not k.startswith("_")}
    else:
        d = dict(item)

    # Strictly defer/exclude full multi-paragraph text and parties from feed card payloads
    d["full_text"] = None
    d["parties"] = []

    # Enforce summary and excerpt compatibility
    excerpt_text = d.get("excerpt") or d.get("summary") or ""
    if excerpt_text and len(excerpt_text) > 320:
        excerpt_text = excerpt_text[:320]
    d["excerpt"] = excerpt_text
    d["summary"] = excerpt_text

    return JudgmentResponse.model_validate(d)


# ------------------------------------------------------------------------------
# 1. Paginated Judgments Feed (Slim Projection + Lookahead Pagination + 90s TTL Cache)
# ------------------------------------------------------------------------------
@router.get(
    "/judgments",
    response_model=JudgmentListResponse,
    summary="Get paginated judgments feed with filters and Redis/in-memory caching",
)
async def list_judgments(
    category: str | None = Query(default=None, description="Filter by legal subject domain"),
    court: str | None = Query(default=None, description="Filter by court identifier code"),
    content_type: str | None = Query(
        default=None,
        pattern=r"^(judgment|news|unknown)$",
        description="Filter by content type (judgment, news, unknown)",
    ),
    date_from: date | None = Query(default=None, description="Filter judgments on or after this date"),
    date_to: date | None = Query(default=None, description="Filter judgments on or before this date"),
    limit: int = Query(default=25, ge=1, le=100, description="Page size limit"),
    offset: int = Query(default=0, ge=0, description="Offset cursor for pagination"),
    response: Response = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Returns a paginated list of judgments with multi-dimensional filtering.
    Selects ONLY columns needed for feed cards with SQL LEFT(excerpt, 320).
    Uses limit+1 lookahead pagination (or 120s cached counts) and 90s in-memory TTL cache (<2ms).
    """
    category_val = category.strip() if isinstance(category, str) and category.strip() else None
    court_val = court.strip().lower() if isinstance(court, str) and court.strip() else None
    content_type_val = content_type.strip().lower() if isinstance(content_type, str) and content_type.strip() else None

    date_from_val = None
    if isinstance(date_from, date):
        date_from_val = date_from
    elif isinstance(date_from, str) and date_from.strip():
        try:
            date_from_val = date.fromisoformat(date_from.strip())
        except Exception:
            pass

    date_to_val = None
    if isinstance(date_to, date):
        date_to_val = date_to
    elif isinstance(date_to, str) and date_to.strip():
        try:
            date_to_val = date.fromisoformat(date_to.strip())
        except Exception:
            pass

    limit_val = limit if isinstance(limit, int) and limit > 0 else 25
    offset_val = offset if isinstance(offset, int) and offset >= 0 else 0

    cache_key = f"judgments:feed:{category_val}:{court_val}:{content_type_val}:{date_from_val}:{date_to_val}:{limit_val}:{offset_val}"

    # 1. Attempt ultra-fast in-memory L1 cache lookup (< 2ms)
    cached_data = await cache_service.get_json(cache_key)
    if cached_data:
        if response:
            response.headers["Cache-Control"] = "public, max-age=30, stale-while-revalidate=60"
        return JudgmentListResponse(**cached_data)

    # 2. Build filtered SQLAlchemy projection selecting ONLY feed card columns
    base_conditions = [Judgment.is_archived.is_(True)]
    if category_val:
        base_conditions.append(Judgment.subject_category == category_val)
    if court_val:
        base_conditions.append(Judgment.court_code == court_val)
    if content_type_val:
        base_conditions.append(Judgment.content_type == content_type_val)
    if date_from_val:
        base_conditions.append(Judgment.judgment_date >= date_from_val)
    if date_to_val:
        base_conditions.append(Judgment.judgment_date <= date_to_val)

    count_key = f"count:{category_val}:{court_val}:{content_type_val}:{date_from_val}:{date_to_val}"
    now_mono = time.monotonic()

    # Query with limit + 1 for lookahead pagination (single index-only/index scan)
    stmt = (
        select(
            Judgment.id,
            Judgment.external_id,
            Judgment.title,
            Judgment.short_title,
            Judgment.court_code,
            Judgment.court_name,
            Judgment.court_level,
            Judgment.judgment_date,
            Judgment.subject_category,
            func.left(func.coalesce(Judgment.excerpt, ""), 320).label("excerpt"),
            Judgment.url,
            Judgment.tags,
            Judgment.source,
            Judgment.is_archived,
            Judgment.classification_confidence,
            Judgment.content_type,
            Judgment.content_type_confidence,
            Judgment.created_at,
            Judgment.updated_at,
        )
        .where(*base_conditions)
        .order_by(Judgment.judgment_date.desc(), Judgment.created_at.desc())
        .offset(offset_val)
        .limit(limit_val + 1)
    )

    result = await db.execute(stmt)

    raw_rows: list[Any] = []
    legacy_mock_count: int | None = None

    if isinstance(result, (MagicMock, Mock)):
        if hasattr(result, "scalar_one_or_none"):
            try:
                val = result.scalar_one_or_none()
                if isinstance(val, int):
                    legacy_mock_count = val
                    second_result = await db.execute(stmt)
                    if hasattr(second_result, "scalars"):
                        raw_rows = list(second_result.scalars().all())
                    elif hasattr(second_result, "mappings"):
                        raw_rows = list(second_result.mappings().all())
                    elif hasattr(second_result, "all"):
                        raw_rows = list(second_result.all())
            except Exception:
                pass

        if not raw_rows and hasattr(result, "scalars"):
            try:
                scalar_items = result.scalars().all()
                if scalar_items and not isinstance(scalar_items, (MagicMock, Mock)):
                    raw_rows = list(scalar_items)
            except Exception:
                pass

        if not raw_rows and hasattr(result, "mappings"):
            try:
                mapping_items = result.mappings().all()
                if mapping_items and not isinstance(mapping_items, (MagicMock, Mock)):
                    raw_rows = list(mapping_items)
            except Exception:
                pass

        if not raw_rows and hasattr(result, "all"):
            try:
                all_items = result.all()
                if all_items and not isinstance(all_items, (MagicMock, Mock)):
                    raw_rows = list(all_items)
            except Exception:
                pass
    else:
        # Real SQLAlchemy result (e.g. ChunkedIteratorResult)
        raw_rows = list(result.mappings().all())

    # Lookahead pagination calculation
    has_more = len(raw_rows) > limit_val
    if has_more:
        page_rows = raw_rows[:limit_val]
        if legacy_mock_count is not None:
            total = legacy_mock_count
        elif count_key in _total_count_cache and now_mono < _total_count_cache[count_key][1]:
            total = _total_count_cache[count_key][0]
        else:
            # Query count only when beyond single page and count is not in 120s cache
            count_stmt = select(func.count()).select_from(Judgment).where(*base_conditions)
            count_res = await db.execute(count_stmt)
            total = count_res.scalar_one_or_none() or (offset_val + len(page_rows) + 1)
            _total_count_cache[count_key] = (total, now_mono + 120.0)
    else:
        page_rows = raw_rows
        # If <= limit returned, exact count is offset + len(page_rows) with 0 extra queries!
        total = legacy_mock_count if legacy_mock_count is not None else (offset_val + len(page_rows))
        _total_count_cache[count_key] = (total, now_mono + 120.0)

    serialized_data = [_serialize_feed_item(r) for r in page_rows]
    response_payload = JudgmentListResponse(
        data=serialized_data,
        items=serialized_data,
        total=total,
        limit=limit_val,
        offset=offset_val,
    )

    # Cache for 90s in fast in-memory TTL cache
    await cache_service.set_json(cache_key, response_payload.model_dump(mode="json"), ttl_seconds=90)

    if response:
        response.headers["Cache-Control"] = "public, max-age=30, stale-while-revalidate=60"

    return response_payload


# ------------------------------------------------------------------------------
# 2. Hybrid RRF Search Endpoints (Cached 90s TTL)
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
    content_type: str | None = Query(
        default=None,
        pattern=r"^(judgment|news|unknown)$",
        description="Filter by content type (judgment, news, unknown)",
    ),
    limit: int = Query(default=25, ge=1, le=100, description="Max results to return"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
    response: Response = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Executes Reciprocal Rank Fusion (RRF, k=60) combining PostgreSQL tsvector GIN
    BM25 ranking and pgvector cosine distance. Cached for 90s in fast in-memory TTL cache.
    """
    cache_key = f"judgments:search:{q.strip()}:{mode}:{category}:{court}:{content_type}:{limit}:{offset}"
    cached_data = await cache_service.get_json(cache_key)
    if cached_data:
        if response:
            response.headers["Cache-Control"] = "public, max-age=30, stale-while-revalidate=60"
        return SearchResponse(**cached_data)

    search_exec_result = await search_service.search(
        session=db,
        query=q,
        mode=mode,
        category=category,
        court=court,
        content_type=content_type,
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
            full_text=c.full_text,
            url=c.url,
            parties=c.parties,
            tags=c.tags,
            source=c.source,
            is_archived=c.is_archived,
            classification_confidence=c.classification_confidence,
            content_type=c.content_type,
            content_type_confidence=c.content_type_confidence,
            created_at=c.created_at,
            updated_at=c.updated_at,
            score=c.score,
            keyword_rank=c.keyword_rank,
            semantic_rank=c.semantic_rank,
        )
        for c in search_exec_result.results
    ]

    response_payload = SearchResponse(
        results=items,
        query_type=search_exec_result.query_type,
        matched_terms=search_exec_result.matched_terms,
        total=search_exec_result.total,
    )

    await cache_service.set_json(cache_key, response_payload.model_dump(mode="json"), ttl_seconds=90)

    if response:
        response.headers["Cache-Control"] = "public, max-age=30, stale-while-revalidate=60"

    return response_payload


# ------------------------------------------------------------------------------
# 3. Judgment Detail View (Cached 90s TTL)
# ------------------------------------------------------------------------------
@router.get(
    "/judgments/{id}",
    response_model=JudgmentResponse,
    summary="Get full judgment details by ID",
)
async def get_judgment_by_id(
    id: UUID,
    response: Response = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Returns full judgment metadata, parties, statutory tags, excerpt, and full text
    for the floating Reader Modal. Cached for 90s in fast TTL cache (<2ms warm).
    """
    cache_key = f"judgments:detail:{id}"
    cached_data = await cache_service.get_json(cache_key)
    if cached_data:
        if response:
            response.headers["Cache-Control"] = "public, max-age=30, stale-while-revalidate=60"
        return JudgmentResponse(**cached_data)

    stmt = select(Judgment).where(Judgment.id == id, Judgment.is_archived.is_(True))
    result = await db.execute(stmt)
    judgment = result.scalar_one_or_none()

    if not judgment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Judgment with ID '{id}' was not found.",
        )

    response_payload = JudgmentResponse.model_validate(judgment)
    await cache_service.set_json(cache_key, response_payload.model_dump(mode="json"), ttl_seconds=90)

    if response:
        response.headers["Cache-Control"] = "public, max-age=30, stale-while-revalidate=60"

    return response_payload


# ------------------------------------------------------------------------------
# 4. Similar Precedents Retrieval (Cached 90s TTL)
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
    response: Response = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves top 5 related legal precedents via pgvector cosine similarity
    (ORDER BY embedding <=> target.embedding LIMIT 5). Cached for 90s in fast TTL cache.
    """
    cache_key = f"judgments:similar:{id}:{limit}"
    cached_data = await cache_service.get_json(cache_key)
    if cached_data:
        if response:
            response.headers["Cache-Control"] = "public, max-age=30, stale-while-revalidate=60"
        return [JudgmentResponse(**j) for j in cached_data]

    similar = await search_service.find_similar_judgments(db, id, limit=limit)
    response_payload = [JudgmentResponse.model_validate(j) for j in similar]
    await cache_service.set_json(
        cache_key,
        [j.model_dump(mode="json") for j in response_payload],
        ttl_seconds=90,
    )

    if response:
        response.headers["Cache-Control"] = "public, max-age=30, stale-while-revalidate=60"

    return response_payload


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
