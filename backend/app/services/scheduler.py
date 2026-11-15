"""
APScheduler Asynchronous Legal Ingestion Scheduler
India Legal News Aggregator - Free-Tier Architecture (< 250 MB RAM)

Schedules periodic ingestion cycles (every 20 minutes by default) using
APScheduler's AsyncIOScheduler with graceful error isolation per feed.
"""

import logging
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

# Global scheduler singleton
_scheduler: AsyncIOScheduler | None = None
_worker: Any | None = None


async def run_scheduled_ingestion_job() -> None:
    """
    Scheduled job callback invoked every 20 minutes by APScheduler.
    Executes an end-to-end ingestion cycle with graceful error isolation.
    """
    global _worker
    if _worker is None:
        from app.workers.ingestion_worker import IngestionWorker
        _worker = IngestionWorker()

    logger.info("Executing scheduled legal RSS ingestion cycle via APScheduler...")
    try:
        report = await _worker.run_once()
        logger.info(
            "Scheduled ingestion cycle finished: %d fetched, %d inserted, %d duplicates",
            report.total_fetched,
            report.total_inserted,
            report.total_duplicates,
        )
    except Exception:
        logger.exception("Error during scheduled ingestion job")


def get_scheduler(interval_minutes: int = 20) -> AsyncIOScheduler:
    """
    Initializes and returns the singleton AsyncIOScheduler configured
    with the 20-minute periodic legal ingestion job.
    """
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler()
        _scheduler.add_job(
            run_scheduled_ingestion_job,
            trigger=IntervalTrigger(minutes=interval_minutes),
            id="legal_rss_ingestion_job",
            name="Periodic Indian Legal RSS Ingestion",
            replace_existing=True,
            coalesce=True,
            max_instances=1,
        )
        logger.info("APScheduler configured with %d-minute legal ingestion job", interval_minutes)
    return _scheduler


def start_scheduler(interval_minutes: int = 20) -> AsyncIOScheduler:
    """
    Starts the APScheduler if not already running.
    """
    sched = get_scheduler(interval_minutes=interval_minutes)
    if not sched.running:
        sched.start()
        logger.info("APScheduler started successfully")
    return sched


def shutdown_scheduler() -> None:
    """
    Gracefully shuts down the APScheduler and any running jobs.
    """
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("APScheduler shut down successfully")
        _scheduler = None
