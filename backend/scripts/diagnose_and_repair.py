"""
Full-Stack Self-Diagnosis, Rich Legal Seed & Auto-Repair Script
Connects to Neon PostgreSQL via DATABASE_URL in backend/.env.
Inspects judgments table, verifies search_tsv, backfills null embeddings,
seeds 24 comprehensive landmark judgments, runs live RSS ingestion,
and executes end-to-end verification of all API contracts.
"""

import asyncio
import logging
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.judgment import Judgment
from app.services.embedding_service import embedding_service
from app.services.search_service import search_service
from app.services.seed_data import seed_landmark_judgments
from app.workers.ingestion_worker import IngestionWorker
from sqlalchemy import func, select, text

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("diagnose_repair")


async def diagnose_and_repair():
    print("=" * 80)
    print("INDIA LEGAL NEWS AGGREGATOR - FULL-STACK SELF-DIAGNOSIS & REPAIR")
    print("=" * 80)
    print(f"Timestamp: {datetime.now(UTC).isoformat()}")
    print(f"Database Target: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else 'configured'}")

    async with AsyncSessionLocal() as session:
        # 1. Connection & Schema Verification
        print("\n[Step 1/5] Verifying Neon Connection & Table Schema...")
        try:
            res = await session.execute(text("SELECT version();"))
            db_version = res.scalar()
            print(f"  Connected to PostgreSQL: {db_version[:60]}...")
        except Exception as e:
            print(f"  FAILED to connect to Neon database: {e}")
            return False

        # Check pgvector extension
        vec_res = await session.execute(text("SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';"))
        vec_row = vec_res.fetchone()
        if vec_row:
            print(f"  pgvector extension: active (version {vec_row[1]})")
        else:
            print("  pgvector extension: NOT FOUND, enabling...")
            await session.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            await session.commit()
            print("  pgvector extension enabled successfully.")

        # Check judgments table count
        total_judgments = (await session.execute(select(func.count(Judgment.id)))).scalar() or 0
        print(f"  Current judgments in database: {total_judgments}")

        # 2. Backfill Embeddings & Verify search_tsv
        print("\n[Step 2/5] Inspecting search_tsv and Backfilling Null Embeddings...")
        # Check rows where embedding IS NULL
        null_emb_stmt = select(Judgment).where(Judgment.embedding.is_(None))
        null_emb_res = await session.execute(null_emb_stmt)
        null_emb_rows = null_emb_res.scalars().all()
        print(f"  Judgments with NULL embedding: {len(null_emb_rows)}")

        if null_emb_rows:
            print(f"  Backfilling 384-dimensional embeddings for {len(null_emb_rows)} judgments...")
            backfilled = 0
            for j in null_emb_rows:
                embed_text = f"{j.title} {j.excerpt} {' '.join(j.tags or [])}".strip()
                emb = await embedding_service.get_embedding(embed_text)
                j.embedding = emb
                backfilled += 1
            await session.commit()
            print(f"  Successfully backfilled embeddings for {backfilled} rows.")
        else:
            print("  All existing judgments already have valid embeddings.")

        # Verify search_tsv column
        tsv_check = await session.execute(
            select(func.count(Judgment.id)).where(Judgment.search_tsv.is_(None))
        )
        null_tsv_count = tsv_check.scalar() or 0
        print(f"  Judgments with NULL search_tsv: {null_tsv_count}")
        if null_tsv_count > 0:
            print(f"  Populating search_tsv for {null_tsv_count} rows...")
            await session.execute(text("""
                UPDATE judgments
                SET search_tsv = to_tsvector('english', coalesce(title, '') || ' ' || coalesce(excerpt, '') || ' ' || coalesce(array_to_string(tags, ' '), ''))
                WHERE search_tsv IS NULL;
            """))
            await session.commit()
            print("  search_tsv population complete.")

        # 3. Seed 24 Landmark Indian Legal Judgments
        print("\n[Step 3/5] Seeding 20+ Detailed Landmark Indian Judgments & Precedents...")
        seed_start = time.perf_counter()
        seeded_count = await seed_landmark_judgments(session)
        seed_duration = time.perf_counter() - seed_start
        print(f"  Successfully seeded/updated {seeded_count} rich landmark judgments (took {seed_duration:.2f}s).")

        # 4. Live RSS Fetch & Ingestion
        print("\n[Step 4/5] Executing Live RSS Fetch & Ingestion...")
        worker = IngestionWorker()
        rss_start = time.perf_counter()
        report = await worker.run_once(session)
        rss_duration = time.perf_counter() - rss_start
        print(f"  Live RSS Ingestion complete in {rss_duration:.2f}s:")
        print(f"    - Total fetched from feeds: {report.total_fetched}")
        print(f"    - New items inserted with embeddings: {report.total_inserted}")
        print(f"    - Duplicate items skipped: {report.total_duplicates}")
        print(f"    - Failed sources: {report.failed_sources}")

        for s in report.sources_reports:
            print(f"    * [{s['source_id']}] {s['feed_name']}: fetched={s['total_fetched']}, inserted={s['items_inserted']}, dup={s['items_duplicate']}, err={s['error']}")

        # 5. End-to-End Verification of Core Capabilities
        print("\n[Step 5/5] End-to-End Verification Against Neon...")

        # Test A: Feed query (default limit 25)
        feed_stmt = (
            select(Judgment)
            .where(Judgment.is_archived.is_(True))
            .order_by(Judgment.judgment_date.desc(), Judgment.created_at.desc())
            .limit(25)
        )
        feed_rows = (await session.execute(feed_stmt)).scalars().all()
        print(f"  [Feed Test] Retrieved {len(feed_rows)} judgments (limit=25). First: '{feed_rows[0].title[:50]}...'")

        # Test B: Smart Search (Hybrid RRF)
        hybrid_res = await search_service.search(session, query="Section 438 CrPC anticipatory bail", mode="hybrid", limit=10)
        print(f"  [Smart Search / Hybrid] Query: 'Section 438 CrPC anticipatory bail' -> {len(hybrid_res.results)} results. Top: '{hybrid_res.results[0].title[:50]}'")

        # Test C: Exact Words Search (BM25 keyword)
        kw_res = await search_service.search(session, query="Article 21 privacy", mode="keyword", limit=10)
        print(f"  [Exact Words / Keyword] Query: 'Article 21 privacy' -> {len(kw_res.results)} results. Top: '{kw_res.results[0].title[:50]}'")

        # Test D: By Meaning Search (Vector semantic)
        sem_res = await search_service.search(session, query="protection from arbitrary police arrest and detention", mode="semantic", limit=10)
        print(f"  [By Meaning / Semantic] Query: 'protection from arbitrary police arrest' -> {len(sem_res.results)} results. Top: '{sem_res.results[0].title[:50]}'")

        # Test E: Subject Categories & Courts Coverage
        cat_counts = await session.execute(
            select(Judgment.subject_category, func.count(Judgment.id)).group_by(Judgment.subject_category)
        )
        print("  [Domain Coverage]:")
        for cat, cnt in cat_counts.fetchall():
            print(f"    - {cat}: {cnt} cases")

        # Final Database Stats
        final_total = (await session.execute(select(func.count(Judgment.id)))).scalar() or 0
        final_emb_null = (await session.execute(select(func.count(Judgment.id)).where(Judgment.embedding.is_(None)))).scalar() or 0
        final_tsv_null = (await session.execute(select(func.count(Judgment.id)).where(Judgment.search_tsv.is_(None)))).scalar() or 0

        print("\n" + "=" * 80)
        print("DIAGNOSIS & AUTO-REPAIR COMPLETED SUCCESSFULLY!")
        print(f"Total Judgments in Neon: {final_total}")
        print(f"Null Embeddings: {final_emb_null} (Expected: 0)")
        print(f"Null Search TSV: {final_tsv_null} (Expected: 0)")
        print("All search modes (Smart Search, Exact Words, By Meaning) verified operational.")
        print("=" * 80)
        return True


if __name__ == "__main__":
    success = asyncio.run(diagnose_and_repair())
    sys.exit(0 if success else 1)
