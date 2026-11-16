"""
Update existing RSS news articles in Neon PostgreSQL with full content text and rich excerpts.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import AsyncSessionLocal
from app.models.judgment import Judgment
from app.services.embedding_service import embedding_service
from app.services.rss_ingestor import DEFAULT_LEGAL_FEEDS, RSSIngestor
from sqlalchemy import select

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("update_rss_news")

async def update_rss_articles():
    bb = [f for f in DEFAULT_LEGAL_FEEDS if f.source_id == "barandbench"][0]
    ingestor = RSSIngestor()
    logger.info("Fetching Bar & Bench feed from %s...", bb.url)
    xml = await ingestor.fetch_feed_xml(bb.url)
    items = ingestor.parse_feed_content(xml, bb)
    logger.info("Parsed %d items from Bar & Bench", len(items))

    async with AsyncSessionLocal() as session:
        updated_count = 0
        inserted_count = 0
        for item in items:
            # Check if exists by external_id or title
            stmt = select(Judgment).where(
                (Judgment.external_id == item.external_id) | (Judgment.title == item.title)
            )
            existing = (await session.execute(stmt)).scalars().first()

            if existing:
                existing.excerpt = item.excerpt
                existing.full_text = item.full_text
                existing.subject_category = item.subject_category
                existing.tags = list(set(existing.tags + item.tags))
                if not existing.embedding:
                    text_for_embed = f"{item.title} {item.subject_category} {item.excerpt}"
                    existing.embedding = embedding_service.embed_query(text_for_embed)
                updated_count += 1
                logger.info("Updated existing article: %s (full_text len: %d)", item.title[:50], len(item.full_text or ""))
            else:
                text_for_embed = f"{item.title} {item.subject_category} {item.excerpt}"
                emb = embedding_service.embed_query(text_for_embed)
                new_j = Judgment(
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
                    parties=[p if isinstance(p, dict) else {"name": str(p), "role": "party"} for p in item.parties],
                    tags=item.tags,
                    source=item.source,
                    is_archived=True,
                    classification_confidence=0.95,
                    embedding=emb,
                )
                session.add(new_j)
                inserted_count += 1
                logger.info("Inserted new article: %s (full_text len: %d)", item.title[:50], len(item.full_text or ""))

        await session.commit()
        logger.info("Successfully updated %d articles and inserted %d articles in Neon DB", updated_count, inserted_count)

if __name__ == "__main__":
    asyncio.run(update_rss_articles())
