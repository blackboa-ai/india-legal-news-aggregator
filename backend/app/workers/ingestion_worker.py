"""
Asynchronous RSS Ingestion Worker & Deduplication Service
India Legal News Aggregator - Free-Tier Architecture (< 250 MB RAM)

Polls Indian legal RSS/Atom feeds on a periodic schedule (15-30 min), performs
database deduplication against existing Judgment records using SHA-256 external_id,
and outputs structured JSON logs. Supports graceful cancellation via asyncio.Event.
"""

import asyncio
import logging
import sys
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Ensure backend root is on sys.path for direct script execution
backend_root = Path(__file__).resolve().parent.parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.judgment import Judgment
from app.services.embedding_service import embedding_service
from app.services.rss_ingestor import (
    DEFAULT_LEGAL_FEEDS,
    FeedSourceConfig,
    ParsedJudgmentItem,
    RSSIngestor,
)

logger = logging.getLogger("app.workers.ingestion")


@dataclass
class FeedIngestionStats:
    """Statistics for a single feed processing operation."""
    source_id: str
    feed_name: str
    total_fetched: int = 0
    items_inserted: int = 0
    items_duplicate: int = 0
    error: str | None = None
    duration_ms: float = 0.0


@dataclass
class IngestionCycleReport:
    """Aggregate statistics for an entire multi-source ingestion cycle."""
    started_at: str
    completed_at: str
    duration_seconds: float
    total_fetched: int = 0
    total_inserted: int = 0
    total_duplicates: int = 0
    failed_sources: int = 0
    sources_reports: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class IngestionWorker:
    """
    Background worker orchestrating periodic RSS scraping, deduplication,
    and PostgreSQL persistence with graceful shutdown mechanics.
    """

    def __init__(
        self,
        interval_seconds: int = 1200,  # 20 minutes default
        feeds: list[FeedSourceConfig] | None = None,
        ingestor: RSSIngestor | None = None,
        session_factory: Callable[[], AsyncSession] | None = None,
    ):
        self.interval_seconds = interval_seconds
        self.feeds = feeds or DEFAULT_LEGAL_FEEDS
        self.ingestor = ingestor or RSSIngestor()
        self.session_factory = session_factory or AsyncSessionLocal
        self._stop_event = asyncio.Event()
        self._is_running = False
        self._worker_task: asyncio.Task | None = None

    @property
    def is_running(self) -> bool:
        return self._is_running

    async def check_exists(self, session: AsyncSession, external_id: str) -> bool:
        """
        Deduplication check: queries whether a Judgment with the given SHA-256 hash exists.
        """
        stmt = select(Judgment.id).where(Judgment.external_id == external_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def persist_item(
        self,
        session: AsyncSession,
        item: ParsedJudgmentItem,
    ) -> bool:
        """
        Persists a parsed judgment into the database if not already present.
        Returns True if inserted, False if skipped as duplicate.
        """
        if await self.check_exists(session, item.external_id):
            return False

        # Generate 384-dim dense vector embedding for hybrid and semantic search
        embed_input = f"{item.title} {item.excerpt} {' '.join(item.tags or [])}".strip()
        embedding = await embedding_service.get_embedding(embed_input)

        judgment = Judgment(
            external_id=item.external_id,
            title=item.title,
            short_title=item.short_title,
            court_code=item.court_code,
            court_name=item.court_name,
            court_level=item.court_level,
            judgment_date=item.judgment_date,
            subject_category=item.subject_category,
            excerpt=item.excerpt,
            full_text=item.full_text,
            url=item.url,
            parties=item.parties,
            tags=item.tags,
            source=item.source,
            is_archived=True,
            classification_confidence=item.classification_confidence,
            embedding=embedding,
        )
        res = session.add(judgment)
        if asyncio.iscoroutine(res):
            await res
        await session.flush()
        return True

    async def ingest_single_feed(
        self,
        session: AsyncSession,
        feed_config: FeedSourceConfig,
    ) -> FeedIngestionStats:
        """
        Fetches, parses, and upserts a single legal feed with error isolation.
        """
        start_time = time.perf_counter()
        stats = FeedIngestionStats(
            source_id=feed_config.source_id,
            feed_name=feed_config.name,
        )

        try:
            items = await self.ingestor.ingest_source(feed_config)
            stats.total_fetched = len(items)

            for item in items:
                try:
                    inserted = await self.persist_item(session, item)
                    if inserted:
                        stats.items_inserted += 1
                    else:
                        stats.items_duplicate += 1
                except (ValueError, TypeError, KeyError) as item_err:
                    logger.warning(
                        "Failed to persist item %s (%s): %s",
                        item.external_id,
                        item.title[:50],
                        str(item_err),
                    )

            await session.commit()
            if stats.items_inserted > 0:
                try:
                    from app.services.cache_service import cache_service
                    await cache_service.clear()
                    logger.info("Invalidated cache after inserting %d records from %s", stats.items_inserted, feed_config.source_id)
                except Exception as cache_err:
                    logger.warning("Failed to invalidate cache after feed insertion: %s", cache_err)

        except Exception as feed_err:
            await session.rollback()
            stats.error = str(feed_err)
            logger.exception(
                "Error processing legal feed '%s'",
                feed_config.name,
            )

        stats.duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return stats

    async def run_once(self, session: AsyncSession | None = None) -> IngestionCycleReport:
        """
        Executes a single end-to-end ingestion cycle across all configured feeds.
        Can be invoked directly by tests, workers, or API endpoints.
        """
        start_wall = datetime.now(UTC).isoformat()
        start_mono = time.perf_counter()

        total_fetched = 0
        total_inserted = 0
        total_duplicates = 0
        failed_sources = 0
        source_reports: list[dict[str, Any]] = []

        logger.info(
            "Starting legal news ingestion cycle for %d sources",
            len(self.feeds),
            extra={"event": "ingestion_cycle_start", "total_sources": len(self.feeds)},
        )

        async def _execute_with_session(db_session: AsyncSession):
            nonlocal total_fetched, total_inserted, total_duplicates, failed_sources

            for feed in self.feeds:
                if self._stop_event.is_set():
                    logger.info("Ingestion cycle interrupted by graceful shutdown request")
                    break

                feed_stats = await self.ingest_single_feed(db_session, feed)
                total_fetched += feed_stats.total_fetched
                total_inserted += feed_stats.items_inserted
                total_duplicates += feed_stats.items_duplicate

                if feed_stats.error:
                    failed_sources += 1

                source_reports.append(asdict(feed_stats))

                logger.info(
                    "Feed %s: %d fetched, %d inserted, %d duplicate (took %.2f ms)",
                    feed.source_id,
                    feed_stats.total_fetched,
                    feed_stats.items_inserted,
                    feed_stats.items_duplicate,
                    feed_stats.duration_ms,
                    extra={
                        "event": "feed_ingested",
                        "source": feed.source_id,
                        "fetched": feed_stats.total_fetched,
                        "inserted": feed_stats.items_inserted,
                        "duplicate": feed_stats.items_duplicate,
                        "duration_ms": feed_stats.duration_ms,
                        "error": feed_stats.error,
                    },
                )

        if session is not None:
            await _execute_with_session(session)
        else:
            async with self.session_factory() as db_session:
                await _execute_with_session(db_session)

        duration = round(time.perf_counter() - start_mono, 2)
        end_wall = datetime.now(UTC).isoformat()

        if total_inserted > 0:
            try:
                from app.services.cache_service import cache_service
                await cache_service.clear()
                logger.info("Invalidated all caches after ingestion cycle inserted %d records", total_inserted)
            except Exception as cache_err:
                logger.warning("Failed to invalidate cache after ingestion cycle: %s", cache_err)

        report = IngestionCycleReport(
            started_at=start_wall,
            completed_at=end_wall,
            duration_seconds=duration,
            total_fetched=total_fetched,
            total_inserted=total_inserted,
            total_duplicates=total_duplicates,
            failed_sources=failed_sources,
            sources_reports=source_reports,
        )

        logger.info(
            "Ingestion cycle completed in %.2fs: %d fetched, %d inserted, %d duplicates, %d failed feeds",
            duration,
            total_fetched,
            total_inserted,
            total_duplicates,
            failed_sources,
            extra={
                "event": "ingestion_cycle_complete",
                "duration_seconds": duration,
                "total_fetched": total_fetched,
                "total_inserted": total_inserted,
                "total_duplicates": total_duplicates,
                "failed_sources": failed_sources,
            },
        )
        return report

    async def _loop(self) -> None:
        """
        Periodic worker loop running every interval_seconds until stop() is invoked.
        """
        self._is_running = True
        logger.info(
            "IngestionWorker background loop active (interval: %d seconds)",
            self.interval_seconds,
        )

        try:
            while not self._stop_event.is_set():
                try:
                    await self.run_once()
                except Exception:
                    logger.exception("Unhandled exception during ingestion cycle")

                # Wait for next interval or graceful shutdown notification
                try:
                    await asyncio.wait_for(
                        self._stop_event.wait(),
                        timeout=float(self.interval_seconds),
                    )
                except TimeoutError:
                    pass
        finally:
            self._is_running = False
            logger.info("IngestionWorker background loop cleanly stopped")

    def start(self) -> asyncio.Task:
        """
        Starts the worker in an asynchronous background asyncio task.
        """
        if self._is_running:
            raise RuntimeError("IngestionWorker is already running")

        self._stop_event.clear()
        self._is_running = True
        self._worker_task = asyncio.create_task(self._loop(), name="ingestion-worker-task")
        return self._worker_task

    def stop(self) -> None:
        """
        Signals the worker loop to shutdown gracefully.
        """
        logger.info("Signaling IngestionWorker shutdown...")
        self._stop_event.set()

    async def stop_and_wait(self) -> None:
        """
        Signals shutdown and awaits complete termination of the task.
        """
        self.stop()
        if self._worker_task and not self._worker_task.done():
            await self._worker_task


# Global default worker instance
ingestion_worker = IngestionWorker()

__all__ = [
    "FeedIngestionStats",
    "IngestionCycleReport",
    "IngestionWorker",
    "ingestion_worker",
]

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    print("Running one-off RSS ingestion cycle...")
    report = asyncio.run(ingestion_worker.run_once())
    print(
        f"Ingestion cycle report: fetched={report.total_fetched}, "
        f"inserted={report.total_inserted}, duplicates={report.total_duplicates}, "
        f"failed_sources={report.failed_sources}, duration={report.duration_seconds}s"
    )
