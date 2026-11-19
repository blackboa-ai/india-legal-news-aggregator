"""
Hybrid Legal Search Service
India Legal News Aggregator - Free-Tier Architecture (< 250 MB RAM)

Combines PostgreSQL tsvector BM25 full-text ranking with pgvector cosine distance
using Reciprocal Rank Fusion (RRF, k=60). Supports multi-dimensional filtering
by legal category, court code, date range, and statutory tags.
"""

import datetime
import hashlib
import logging
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.judgment import Judgment
from app.services.cache_service import cache_service
from app.services.embedding_service import embedding_service

logger = logging.getLogger("app.services.search")

# RRF default constant recommended in information retrieval literature
RRF_K_DEFAULT = 60


@dataclass
class SearchCandidate:
    """Internal representation of a candidate judgment scored during search."""
    id: UUID
    external_id: str
    title: str
    short_title: str | None
    court_code: str
    court_name: str
    court_level: int
    judgment_date: datetime.date
    subject_category: str
    excerpt: str
    url: str
    tags: list[str] = field(default_factory=list)
    source: str = ""
    parties: list[dict[str, Any]] = field(default_factory=list)
    full_text: str | None = None
    is_archived: bool = True
    classification_confidence: float = 0.0
    content_type: str = "unknown"
    content_type_confidence: float = 0.0
    created_at: datetime.datetime | None = None
    updated_at: datetime.datetime | None = None
    score: float = 0.0
    keyword_rank: int | None = None
    semantic_rank: int | None = None


@dataclass
class SearchExecutionResult:
    """Aggregated search result with metadata."""
    results: list[SearchCandidate]
    query_type: str
    matched_terms: list[str]
    total: int


def compute_rrf(
    keyword_items: Sequence[dict[str, Any]],
    semantic_items: Sequence[dict[str, Any]],
    k: int = RRF_K_DEFAULT,
    apply_judgment_boost: bool = True,
    judgment_boost_factor: float = 1.15,
) -> list[dict[str, Any]]:
    """
    Computes Reciprocal Rank Fusion (RRF) scores across keyword and semantic ranked lists.
    Formula: RRF_score(d) = sum_{m in models} 1 / (k + rank_m(d))
    Ranks are 1-based (1, 2, ...).
    Applies optional multiplier boost for authoritative 'judgment' content types.
    """
    scores: dict[Any, float] = {}
    combined_items: dict[Any, dict[str, Any]] = {}
    kw_ranks: dict[Any, int] = {}
    sem_ranks: dict[Any, int] = {}

    # 1. Process keyword ranks
    for rank_idx, item in enumerate(keyword_items, start=1):
        item_id = item["id"]
        kw_ranks[item_id] = rank_idx
        scores[item_id] = scores.get(item_id, 0.0) + (1.0 / (k + rank_idx))
        if item_id not in combined_items:
            combined_items[item_id] = dict(item)

    # 2. Process semantic ranks
    for rank_idx, item in enumerate(semantic_items, start=1):
        item_id = item["id"]
        sem_ranks[item_id] = rank_idx
        scores[item_id] = scores.get(item_id, 0.0) + (1.0 / (k + rank_idx))
        if item_id not in combined_items:
            combined_items[item_id] = dict(item)

    # 3. Compile sorted output with judgment boost
    ranked_list = []
    for item_id, item_data in combined_items.items():
        base_score = scores[item_id]
        c_type = item_data.get("content_type") or "unknown"
        if apply_judgment_boost and c_type == "judgment":
            final_score = base_score * judgment_boost_factor
        else:
            final_score = base_score

        res = dict(item_data)
        res["score"] = round(final_score, 6)
        res["keyword_rank"] = kw_ranks.get(item_id)
        res["semantic_rank"] = sem_ranks.get(item_id)
        ranked_list.append(res)

    ranked_list.sort(key=lambda x: x["score"], reverse=True)
    return ranked_list


def extract_matched_terms(query: str) -> list[str]:
    """
    Extracts legal search tokens, statutory citations, and keywords from the search string.
    Highlights terms like 'Section 438 CrPC', 'Article 21', 'Section 138', etc.
    """
    terms: list[str] = []
    if not query:
        return terms

    # Extract statutory patterns
    statute_patterns = [
        r"(?:Section|Sec\.?)\s+\d+[\w\s]*(?:CrPC|IPC|CPC|BNSS|BNS|NI\s+Act|IBC|IT\s+Act)?",
        r"Article\s+\d+[\w\s]*",
        r"Order\s+[IVXLCDM]+\s+Rule\s+\d+",
        r"\b(?:anticipatory\s+bail|quashing|habeas\s+corpus|mandamus|certiorari|fundamental\s+rights|cheque\s+bounce|interim\s+injunction)\b",
    ]
    for pat in statute_patterns:
        matches = re.findall(pat, query, re.IGNORECASE)
        for m in matches:
            clean_m = m.strip()
            if clean_m and clean_m not in terms:
                terms.append(clean_m)

    # Extract general keywords (>= 3 chars, or 2-char legal acronyms) not already captured
    two_letter_acronyms = {"ed", "it", "sc", "hc", "ni", "cr", "pc", "ib", "ip"}
    words = re.findall(r"\b[A-Za-z0-9_-]{2,}\b", query)
    stop_words = {
        "the", "and", "for", "with", "from", "that", "this", "under", "court",
        "judge", "in", "to", "of", "on", "at", "by", "an", "as", "is", "or",
    }
    for w in words:
        w_lower = w.lower()
        if len(w) == 2 and w_lower not in two_letter_acronyms and not w.isupper():
            continue
        if w_lower not in stop_words and not any(w_lower in t.lower() for t in terms):
            terms.append(w)

    return terms


class SearchService:
    """
    Hybrid legal search combining PostgreSQL tsvector BM25 and pgvector cosine distance.
    Provides sub-100ms query construction and flexible query modes (hybrid, keyword, semantic).
    """

    def __init__(self, rrf_k: int = RRF_K_DEFAULT):
        self.rrf_k = rrf_k

    def build_filter_clauses(
        self,
        category: str | None = None,
        court: str | None = None,
        date_from: datetime.date | None = None,
        date_to: datetime.date | None = None,
        citation: str | None = None,
        content_type: str | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """
        Builds dynamic parameterized SQL WHERE clauses and parameter dictionary.
        Prevents SQL injection using named parameters.
        """
        clauses: list[str] = ["is_archived = true"]
        params: dict[str, Any] = {}

        if category:
            clauses.append("subject_category = :category")
            params["category"] = category.strip()

        if court:
            clauses.append("court_code = :court")
            params["court"] = court.strip().lower()

        if date_from:
            clauses.append("judgment_date >= :date_from")
            params["date_from"] = date_from

        if date_to:
            clauses.append("judgment_date <= :date_to")
            params["date_to"] = date_to

        if citation:
            clauses.append("(:citation = ANY(tags) OR title ILIKE :citation_like)")
            params["citation"] = citation.strip()
            params["citation_like"] = f"%{citation.strip()}%"

        if content_type:
            clauses.append("content_type = :content_type")
            params["content_type"] = content_type.strip().lower()

        where_sql = " AND ".join(clauses)
        return where_sql, params

    async def execute_keyword_search(
        self,
        session: AsyncSession,
        query: str,
        where_sql: str,
        params: dict[str, Any],
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """
        Executes PostgreSQL tsvector full-text search with ts_rank_cd ranking.
        Falls back to comprehensive ILIKE matching across title, excerpt, full_text,
        and statutory tags if tsvector returns 0 rows or encounters a tsquery syntax issue.
        """
        sql = f"""
        SELECT
            id, external_id, title, short_title, court_code, court_name, court_level,
            judgment_date, subject_category, excerpt, full_text, url, parties, tags, source,
            is_archived, classification_confidence, content_type, content_type_confidence,
            created_at, updated_at,
            ts_rank_cd(search_tsv, websearch_to_tsquery('english', :query)) as rank_score
        FROM judgments
        WHERE {where_sql}
          AND search_tsv @@ websearch_to_tsquery('english', :query)
        ORDER BY rank_score DESC
        LIMIT :limit;
        """
        exec_params = {**params, "query": query, "limit": limit}

        try:
            result = await session.execute(text(sql), exec_params)
            rows = result.mappings().all()
            if rows:
                return [dict(r) for r in rows]
        except Exception as e:
            logger.debug("tsvector query failed, running ILIKE fallback: %s", e)

        # Fallback for plain ILIKE matching across title, excerpt, full_text, and tags
        fallback_sql = f"""
        SELECT
            id, external_id, title, short_title, court_code, court_name, court_level,
            judgment_date, subject_category, excerpt, full_text, url, parties, tags, source,
            is_archived, classification_confidence, content_type, content_type_confidence,
            created_at, updated_at,
            CASE
                WHEN title ILIKE :q_like THEN 1.5
                WHEN excerpt ILIKE :q_like THEN 1.2
                WHEN full_text ILIKE :q_like THEN 1.0
                ELSE 0.8
            END as rank_score
        FROM judgments
        WHERE {where_sql}
          AND (
              title ILIKE :q_like
              OR excerpt ILIKE :q_like
              OR full_text ILIKE :q_like
              OR :query = ANY(tags)
          )
        ORDER BY rank_score DESC, judgment_date DESC
        LIMIT :limit;
        """
        fb_params = {**params, "q_like": f"%{query}%", "query": query, "limit": limit}
        try:
            result = await session.execute(text(fallback_sql), fb_params)
            return [dict(r) for r in result.mappings().all()]
        except Exception as fb_err:
            logger.debug("ILIKE fallback query failed: %s", fb_err)
            return []

    async def execute_semantic_search(
        self,
        session: AsyncSession,
        query_vector: list[float],
        where_sql: str,
        params: dict[str, Any],
        limit: int = 20,
        min_similarity: float = 0.08,
    ) -> list[dict[str, Any]]:
        """
        Executes pgvector cosine similarity search (<=> operator) against Judgment.embedding.
        Filters out low-similarity candidates below min_similarity threshold to prevent
        completely unrelated noise/hallucinations on out-of-domain queries.
        """
        # Convert vector to Postgres vector literal string '[0.1, 0.2, ...]'
        vec_str = f"[{','.join(f'{x:.6f}' for x in query_vector)}]"

        sql = f"""
        SELECT
            id, external_id, title, short_title, court_code, court_name, court_level,
            judgment_date, subject_category, excerpt, full_text, url, parties, tags, source,
            is_archived, classification_confidence, content_type, content_type_confidence,
            created_at, updated_at,
            1.0 - (embedding <=> CAST(:query_vec AS vector)) as sim_score
        FROM judgments
        WHERE {where_sql}
          AND embedding IS NOT NULL
        ORDER BY embedding <=> CAST(:query_vec AS vector) ASC
        LIMIT :limit;
        """
        exec_params = {**params, "query_vec": vec_str, "limit": limit}

        try:
            result = await session.execute(text(sql), exec_params)
            rows = result.mappings().all()
            return [dict(r) for r in rows if float(r.get("sim_score", 0.0) or 0.0) >= min_similarity]
        except Exception as e:
            logger.warning("pgvector similarity search failed: %s", e)
            return []

    async def search(
        self,
        session: AsyncSession,
        query: str,
        mode: str = "hybrid",
        category: str | None = None,
        court: str | None = None,
        date_from: datetime.date | None = None,
        date_to: datetime.date | None = None,
        citation: str | None = None,
        content_type: str | None = None,
        limit: int = 10,
        offset: int = 0,
    ) -> SearchExecutionResult:
        """
        Main entrypoint for hybrid, keyword, and semantic legal search.
        """
        cache_key = f"search:{hashlib.sha256(f'{query}:{category}:{court}:{date_from}:{date_to}:{content_type}'.encode()).hexdigest()}"
        cached_result = await cache_service.get(cache_key)
        if cached_result is not None and isinstance(cached_result, SearchExecutionResult):
            return cached_result

        clean_query = query.strip()
        matched_terms = extract_matched_terms(clean_query)
        where_sql, params = self.build_filter_clauses(
            category=category,
            court=court,
            date_from=date_from,
            date_to=date_to,
            citation=citation,
            content_type=content_type,
        )

        mode_normalized = mode.lower()
        if mode_normalized not in ("hybrid", "keyword", "semantic"):
            mode_normalized = "hybrid"

        # Candidate pool size for fusion
        candidate_limit = max(limit * 2, 20)

        keyword_items: list[dict[str, Any]] = []
        semantic_items: list[dict[str, Any]] = []

        if mode_normalized in ("hybrid", "keyword"):
            keyword_items = await self.execute_keyword_search(
                session=session,
                query=clean_query,
                where_sql=where_sql,
                params=params,
                limit=candidate_limit,
            )

        if mode_normalized in ("hybrid", "semantic"):
            query_vector = await embedding_service.get_embedding(clean_query)
            semantic_items = await self.execute_semantic_search(
                session=session,
                query_vector=query_vector,
                where_sql=where_sql,
                params=params,
                limit=candidate_limit,
            )

        # ----------------------------------------------------------------------
        # Rank Aggregation / Fusion
        # ----------------------------------------------------------------------
        if mode_normalized == "hybrid":
            ranked_dicts = compute_rrf(keyword_items, semantic_items, k=self.rrf_k)
        elif mode_normalized == "keyword":
            ranked_dicts = []
            for idx, item in enumerate(keyword_items, start=1):
                d = dict(item)
                d["score"] = float(d.get("rank_score", 1.0))
                d["keyword_rank"] = idx
                d["semantic_rank"] = None
                ranked_dicts.append(d)
        else:  # semantic
            ranked_dicts = []
            for idx, item in enumerate(semantic_items, start=1):
                d = dict(item)
                d["score"] = float(d.get("sim_score", 1.0))
                d["keyword_rank"] = None
                d["semantic_rank"] = idx
                ranked_dicts.append(d)

        total_candidates = len(ranked_dicts)
        sliced = ranked_dicts[offset : offset + limit]

        candidates = [
            SearchCandidate(
                id=UUID(str(r["id"])) if not isinstance(r["id"], UUID) else r["id"],
                external_id=str(r["external_id"]),
                title=str(r["title"]),
                short_title=r.get("short_title"),
                court_code=str(r["court_code"]),
                court_name=str(r["court_name"]),
                court_level=int(r.get("court_level", 2)),
                judgment_date=r["judgment_date"],
                subject_category=str(r["subject_category"]),
                excerpt=str(r["excerpt"]),
                url=str(r["url"]),
                tags=list(r.get("tags") or []),
                source=str(r.get("source", "")),
                parties=list(r.get("parties") or []),
                full_text=r.get("full_text"),
                is_archived=bool(r.get("is_archived", True)),
                classification_confidence=float(r.get("classification_confidence", 0.0)),
                content_type=str(r.get("content_type") or "unknown"),
                content_type_confidence=float(r.get("content_type_confidence", 0.0) or 0.0),
                created_at=r.get("created_at"),
                updated_at=r.get("updated_at"),
                score=float(r.get("score", 0.0)),
                keyword_rank=r.get("keyword_rank"),
                semantic_rank=r.get("semantic_rank"),
            )
            for r in sliced
        ]

        execution_result = SearchExecutionResult(
            results=candidates,
            query_type=mode_normalized,
            matched_terms=matched_terms if total_candidates > 0 else [],
            total=total_candidates,
        )
        await cache_service.set(cache_key, execution_result, ttl_seconds=900)
        return execution_result

    async def find_similar_judgments(
        self,
        session: AsyncSession,
        judgment_id: UUID,
        limit: int = 5,
    ) -> list[Judgment]:
        """
        Finds top related legal precedents via pgvector cosine distance:
        ORDER BY embedding <=> target.embedding LIMIT 5.
        """
        # Fetch target judgment's embedding and subject category
        stmt = text("SELECT id, subject_category, embedding FROM judgments WHERE id = :id;")
        res = await session.execute(stmt, {"id": str(judgment_id)})
        target = res.mappings().one_or_none()
        if not target:
            return []

        target_embedding = target.get("embedding")
        target_category = target.get("subject_category")

        if target_embedding is not None:
            # Vector similarity search in pgvector
            vec_str = (
                f"[{','.join(f'{x:.6f}' for x in target_embedding)}]"
                if isinstance(target_embedding, (list, tuple))
                else str(target_embedding)
            )
            sql = """
            SELECT id, external_id, title, short_title, court_code, court_name, court_level,
                   judgment_date, subject_category, excerpt, full_text, url, parties, tags,
                   source, is_archived, classification_confidence, created_at, updated_at
            FROM judgments
            WHERE id != :target_id
              AND is_archived = true
              AND embedding IS NOT NULL
            ORDER BY embedding <=> CAST(:target_vec AS vector) ASC
            LIMIT :limit;
            """
            similar_res = await session.execute(
                text(sql),
                {"target_id": str(judgment_id), "target_vec": vec_str, "limit": limit},
            )
        else:
            # Fallback by subject category
            sql = """
            SELECT id, external_id, title, short_title, court_code, court_name, court_level,
                   judgment_date, subject_category, excerpt, full_text, url, parties, tags,
                   source, is_archived, classification_confidence, created_at, updated_at
            FROM judgments
            WHERE id != :target_id
              AND is_archived = true
              AND subject_category = :category
            ORDER BY judgment_date DESC
            LIMIT :limit;
            """
            similar_res = await session.execute(
                text(sql),
                {"target_id": str(judgment_id), "category": target_category, "limit": limit},
            )

        rows = similar_res.mappings().all()
        judgments = []
        for r in rows:
            j = Judgment(
                id=r["id"],
                external_id=r["external_id"],
                title=r["title"],
                short_title=r["short_title"],
                court_code=r["court_code"],
                court_name=r["court_name"],
                court_level=r["court_level"],
                judgment_date=r["judgment_date"],
                subject_category=r["subject_category"],
                excerpt=r["excerpt"],
                full_text=r["full_text"],
                url=r["url"],
                parties=r["parties"] or [],
                tags=r["tags"] or [],
                source=r["source"],
                is_archived=r["is_archived"],
                classification_confidence=r["classification_confidence"],
                created_at=r["created_at"],
                updated_at=r["updated_at"],
            )
            judgments.append(j)
        return judgments


# Singleton search service instance
search_service = SearchService()
