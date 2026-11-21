"""
Asynchronous Legal RSS / Atom Ingestion Pipeline
India Legal News Aggregator - Free-Tier Architecture (< 250 MB RAM)

Fetches legal feeds from Supreme Court of India, Indian Kanoon, LiveLaw, and
Bar & Bench. Performs HTML sanitization, whitespace normalization, SHA-256
deterministic external_id computation, and legal categorization.
"""

import asyncio
import datetime
import hashlib
import html
import logging
import re
import urllib.parse
from dataclasses import asdict, dataclass
from typing import Any

import feedparser
import httpx
from bs4 import BeautifulSoup

from app.services.legal_classifier import CourtInfo, LegalClassifier, classify_content_type

logger = logging.getLogger(__name__)

# Standard browser User-Agent adhering to Indian court & legal publication etiquette
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# Tracking query parameters to strip during URL canonicalization
TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "ref",
    "fbclid",
    "gclid",
    "_hsenc",
    "_hsmi",
    "mc_cid",
    "mc_eid",
}


@dataclass
class FeedSourceConfig:
    """Configuration definition for an Indian legal RSS/Atom feed source."""
    source_id: str  # 'sci', 'indiankanoon', 'livelaw', 'barandbench'
    name: str
    url: str
    default_court_code: str = "sc"
    default_court_name: str = "Supreme Court of India"
    default_court_level: int = 1
    enabled: bool = True


# Pre-configured legal sources covering Supreme Court, Kanoon High Courts, LiveLaw, Bar & Bench
DEFAULT_LEGAL_FEEDS: list[FeedSourceConfig] = [
    FeedSourceConfig(
        source_id="sci",
        name="Supreme Court of India Judgments",
        url="https://sci.gov.in/rss/judgments.xml",
        default_court_code="sc",
        default_court_name="Supreme Court of India",
        default_court_level=1,
        enabled=False,  # SCI official site decommissioned XML feeds in WordPress redesign
    ),
    FeedSourceConfig(
        source_id="indiankanoon",
        name="Supreme Court of India (Kanoon)",
        url="https://indiankanoon.org/feeds/latest/supremecourt/",
        default_court_code="sc",
        default_court_name="Supreme Court of India",
        default_court_level=1,
    ),
    FeedSourceConfig(
        source_id="indiankanoon",
        name="Delhi High Court (Kanoon)",
        url="https://indiankanoon.org/feeds/latest/delhi/",
        default_court_code="delhi-hc",
        default_court_name="High Court of Delhi",
        default_court_level=2,
    ),
    FeedSourceConfig(
        source_id="indiankanoon",
        name="Bombay High Court (Kanoon)",
        url="https://indiankanoon.org/feeds/latest/bombay/",
        default_court_code="bombay-hc",
        default_court_name="High Court of Bombay",
        default_court_level=2,
    ),
    FeedSourceConfig(
        source_id="indiankanoon",
        name="Allahabad High Court (Kanoon)",
        url="https://indiankanoon.org/feeds/latest/allahabad/",
        default_court_code="allahabad-hc",
        default_court_name="High Court of Allahabad",
        default_court_level=2,
    ),
    FeedSourceConfig(
        source_id="indiankanoon",
        name="Calcutta High Court (Kanoon)",
        url="https://indiankanoon.org/feeds/latest/kolkata/",
        default_court_code="calcutta-hc",
        default_court_name="High Court of Calcutta",
        default_court_level=2,
    ),
    FeedSourceConfig(
        source_id="indiankanoon",
        name="Madras High Court (Kanoon)",
        url="https://indiankanoon.org/feeds/latest/chennai/",
        default_court_code="madras-hc",
        default_court_name="High Court of Madras",
        default_court_level=2,
    ),
    FeedSourceConfig(
        source_id="livelaw",
        name="LiveLaw Legal News & Judgments",
        url="https://www.livelaw.in/google_feeds.xml",
        default_court_code="sc",
        default_court_name="Supreme Court of India",
        default_court_level=1,
    ),
    FeedSourceConfig(
        source_id="barandbench",
        name="Bar & Bench Legal News",
        url="https://www.barandbench.com/stories.rss",
        default_court_code="sc",
        default_court_name="Supreme Court of India",
        default_court_level=1,
    ),
    FeedSourceConfig(
        source_id="bbc",
        name="BBC World Breaking News",
        url="https://feeds.bbci.co.uk/news/world/rss.xml",
        default_court_code="international",
        default_court_name="International Breaking News",
        default_court_level=4,
        enabled=True,
    ),
]


@dataclass
class ParsedJudgmentItem:
    """Fully parsed and classified legal item ready for database upsert."""
    external_id: str
    title: str
    short_title: str
    court_code: str
    court_name: str
    court_level: int
    judgment_date: datetime.date
    subject_category: str
    excerpt: str
    full_text: str | None
    url: str
    parties: list[dict[str, str]]
    tags: list[str]
    source: str
    classification_confidence: float
    content_type: str = "unknown"
    content_type_confidence: float = 0.0
    image_url: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def sanitize_html_text(raw_html: str | None, preserve_newlines: bool = False) -> str:
    """
    Safely strips HTML tags, script/style blocks, and unescapes entities.
    Normalizes excessive whitespace into single spaces or double newlines.
    """
    if not raw_html:
        return ""

    sep = "\n\n" if preserve_newlines else " "
    if "<" not in raw_html:
        text = raw_html
    else:
        try:
            soup = BeautifulSoup(raw_html, "html.parser")
            # Remove active or formatting markup tags
            for element in soup(["script", "style", "noscript", "iframe", "header", "footer", "nav", "aside"]):
                element.decompose()

            text = soup.get_text(separator=sep)
        except (ValueError, TypeError, AttributeError):
            # Fallback regex tag stripping in case of malformed markup
            text = re.sub(r"<[^>]+>", sep, raw_html)

    # Unescape HTML entities (&nbsp;, &amp;, &#39;, etc.)
    text = html.unescape(text)
    # Normalize non-breaking spaces and whitespace
    text = text.replace("\xa0", " ").replace("\u200b", "")
    # Remove space before punctuation marks (. , : ; ? !)
    text = re.sub(r"[ \t]+([,.:;?!])", r"\1", text)
    if preserve_newlines:
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n\s*\n+", "\n\n", text).strip()
    else:
        text = re.sub(r"\s+", " ", text).strip()
    return text


def canonicalize_url(raw_url: str) -> str:
    """
    Normalizes a URL by stripping tracking parameters, normalizing hostnames,
    and removing trailing slashes/fragments to ensure stable deduplication.
    """
    if not raw_url:
        return ""

    raw_url = raw_url.strip()
    try:
        parsed = urllib.parse.urlsplit(raw_url)
        # Lowercase scheme and hostname
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()
        path = parsed.path.rstrip("/") if parsed.path != "/" else "/"

        # Filter out tracking query parameters
        query_params = urllib.parse.parse_qsl(parsed.query, keep_blank_values=False)
        clean_params = [
            (k, v) for k, v in query_params if k.lower() not in TRACKING_PARAMS
        ]
        # Sort query params deterministically
        clean_params.sort(key=lambda x: (x[0], x[1]))
        clean_query = urllib.parse.urlencode(clean_params)

        return urllib.parse.urlunsplit((scheme, netloc, path, clean_query, ""))
    except (ValueError, TypeError, AttributeError):
        return raw_url.rstrip("/")


def compute_external_id(canonical_url: str, normalized_title: str) -> str:
    """
    Generates a deterministic SHA-256 hash from canonical URL + normalized title.
    Acts as the unique deduplication key for Judgment records.
    """
    url_part = canonicalize_url(canonical_url)
    # Normalize title: strip whitespace, unescape entities, lowercase
    title_part = re.sub(r"\s+", " ", html.unescape(normalized_title)).strip().lower()

    fingerprint = f"{url_part}|{title_part}".encode()
    return hashlib.sha256(fingerprint).hexdigest()


class RSSIngestor:
    """
    Asynchronous RSS and Atom feed ingestor with exponential backoff,
    polite headers, HTML sanitization, and legal classification.
    """

    def __init__(
        self,
        user_agent: str = DEFAULT_USER_AGENT,
        timeout: float = 20.0,
        max_retries: int = 3,
        backoff_factor: float = 1.5,
    ):
        self.user_agent = user_agent
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

    async def fetch_feed_xml(
        self,
        url: str,
        client: httpx.AsyncClient | None = None,
    ) -> str:
        """
        Fetches feed XML with exponential backoff retries.
        """
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, text/html, */*",
            "Accept-Language": "en-US,en;q=0.9",
        }

        should_close = False
        if client is None:
            client = httpx.AsyncClient(timeout=self.timeout, follow_redirects=True)
            should_close = True

        try:
            for attempt in range(1, self.max_retries + 1):
                try:
                    logger.debug("Fetching RSS feed %s (attempt %d/%d)", url, attempt, self.max_retries)
                    response = await client.get(url, headers=headers)
                    response.raise_for_status()
                    return response.text
                except (httpx.HTTPError, httpx.TimeoutException) as exc:
                    logger.warning(
                        "Error fetching RSS feed %s on attempt %d/%d: %s",
                        url,
                        attempt,
                        self.max_retries,
                        str(exc),
                    )
                    if attempt == self.max_retries:
                        raise
                    delay = self.backoff_factor ** attempt
                    await asyncio.sleep(delay)
        finally:
            if should_close:
                await client.aclose()

        raise RuntimeError(f"Failed to fetch feed from {url} after {self.max_retries} attempts")

    def parse_feed_content(
        self,
        feed_content: str,
        source_config: FeedSourceConfig,
    ) -> list[ParsedJudgmentItem]:
        """
        Parses XML / RSS / Atom string and returns structured ParsedJudgmentItem instances.
        Enriches each record via LegalClassifier for domain, statutes, court, and parties.
        """
        parsed_feed = feedparser.parse(feed_content)
        items: list[ParsedJudgmentItem] = []
        seen_batch_hashes: set[str] = set()

        default_court = CourtInfo(
            court_code=source_config.default_court_code,
            court_name=source_config.default_court_name,
            court_level=source_config.default_court_level,
        )

        for entry in parsed_feed.entries:
            raw_title = entry.get("title", "")
            title = sanitize_html_text(raw_title)
            if not title:
                continue

            # Link canonicalization
            raw_url = entry.get("link", "")
            canonical_url = canonicalize_url(raw_url)
            if not canonical_url:
                continue

            # Deterministic SHA-256 deduplication ID
            external_id = compute_external_id(canonical_url, title)

            # Content payload extraction & cleaning
            content_values = [
                c.get("value", "") for c in entry.get("content", []) if isinstance(c, dict) and c.get("value")
            ]
            content_html = "\n\n".join(content_values) if content_values else ""

            raw_summary = (
                entry.get("summary")
                or entry.get("description")
                or ""
            )
            raw_excerpt = sanitize_html_text(raw_summary)

            # Extract full text if provided in content payload or rich summary
            full_text = None
            if content_html:
                candidate_content = sanitize_html_text(content_html, preserve_newlines=True)
                if candidate_content:
                    full_text = candidate_content
            elif len(raw_summary) > 300:
                candidate_content = sanitize_html_text(raw_summary, preserve_newlines=True)
                if candidate_content:
                    full_text = candidate_content

            # Ensure clean summary excerpt (not identical to the title if full text is available)
            if raw_excerpt and raw_excerpt.strip() != title.strip():
                excerpt = raw_excerpt
            elif full_text:
                paragraphs = [p.strip() for p in full_text.split("\n\n") if p.strip() and len(p.strip()) > 30]
                if paragraphs:
                    excerpt = paragraphs[0]
                else:
                    excerpt = full_text[:400]
            else:
                excerpt = title

            # Parse judgment or publication date
            judgment_date = self._extract_date(entry)

            # Image URL extraction (media:thumbnail, media:content, enclosures)
            image_url = None
            media_thumbnails = entry.get("media_thumbnail", [])
            if media_thumbnails and isinstance(media_thumbnails, list) and media_thumbnails[0].get("url"):
                raw_img = media_thumbnails[0]["url"]
                # For BBC images, upscale standard 240 thumbnail to high-res 800 for crisp 16:9 hero banner
                image_url = raw_img.replace("/standard/240/", "/standard/800/")
            elif entry.get("media_content"):
                media_content = entry.get("media_content", [])
                if media_content and isinstance(media_content, list) and media_content[0].get("url"):
                    image_url = media_content[0]["url"]
            elif entry.get("enclosures"):
                enclosures = entry.get("enclosures", [])
                for enc in enclosures:
                    if isinstance(enc, dict) and enc.get("type", "").startswith("image/"):
                        image_url = enc.get("href")
                        break

            # Batch connected petition deduplication: if identical excerpt/text was already processed in this batch, skip clone
            if excerpt and len(excerpt) > 50 and excerpt != title:
                excerpt_fp = hashlib.sha256(re.sub(r"\s+", " ", excerpt[:250]).strip().lower().encode()).hexdigest()
                if excerpt_fp in seen_batch_hashes:
                    logger.debug("Skipping duplicate batch connected petition in feed: %s", title[:80])
                    continue
                seen_batch_hashes.add(excerpt_fp)

            # Run deterministic legal classification and metadata extraction
            classification = LegalClassifier.classify(
                title=title,
                text=excerpt,
                source=source_config.source_id,
                default_court=default_court,
                url=canonical_url,
            )

            # 3-State content classification (judgment, news, unknown)
            content_type, content_type_confidence = classify_content_type(
                title=title,
                text=full_text or excerpt,
                source=source_config.source_id,
                url=canonical_url,
            )

            # Court resolution: classification overrides if high confidence or fallback to source default
            court = classification.court or default_court

            # Short title (first 500 characters)
            short_title = title[:500]

            item = ParsedJudgmentItem(
                external_id=external_id,
                title=title,
                short_title=short_title,
                court_code=court.court_code,
                court_name=court.court_name,
                court_level=court.court_level,
                judgment_date=judgment_date,
                subject_category=classification.subject_category,
                excerpt=excerpt or title,
                full_text=full_text,
                url=canonical_url,
                parties=classification.parties,
                tags=classification.statute_tags,
                source=source_config.source_id,
                classification_confidence=classification.confidence,
                content_type=content_type,
                content_type_confidence=content_type_confidence,
                image_url=image_url,
            )
            items.append(item)

        return items

    @staticmethod
    def extract_article_text_from_html(html_text: str) -> tuple[str | None, str | None]:
        """
        Extracts clean summary excerpt and full body narrative text from news article HTML markup.
        Compatible with LiveLaw, Bar & Bench, Indian Kanoon, and general legal portals.
        """
        if not html_text:
            return None, None

        try:
            soup = BeautifulSoup(html_text, "html.parser")

            # 1. Extract meta description for crisp summary excerpt
            meta_desc = (
                soup.find("meta", attrs={"name": "description"})
                or soup.find("meta", attrs={"property": "og:description"})
                or soup.find("meta", attrs={"name": "twitter:description"})
            )
            raw_desc = meta_desc.get("content", "").strip() if meta_desc else ""
            excerpt = sanitize_html_text(raw_desc) if raw_desc else None

            # 2. Extract article container
            article_div = soup.find(
                "div",
                class_=lambda c: c and any(
                    k in str(c).lower()
                    for k in [
                        "story-content",
                        "story-detail",
                        "story_detail",
                        "content-detail",
                        "article-body",
                        "post-content",
                        "doc_content",
                        "judgments",
                    ]
                ),
            ) or soup.find("article")

            paragraphs: list[str] = []
            if article_div:
                for tag in article_div(["script", "style", "noscript", "iframe", "form", "button"]):
                    tag.decompose()

                # Extract block-level tags (p, pre, blockquote)
                block_tags = article_div.find_all(["p", "pre", "blockquote"])
                if block_tags:
                    for b in block_tags:
                        raw_block = b.get_text().strip()
                        # If pre block has multiple internal paragraphs, preserve paragraph division
                        sub_chunks = raw_block.split("\n\n") if b.name == "pre" else [raw_block]
                        for chunk in sub_chunks:
                            text = chunk.strip()
                            if len(text) > 30 and not any(
                                skip in text.lower()
                                for skip in [
                                    "share this",
                                    "listen to this article",
                                    "click here to download",
                                    "also read",
                                    "read full story",
                                    "subscribe to livelaw",
                                ]
                            ):
                                cleaned = sanitize_html_text(text, preserve_newlines=(b.name == "pre"))
                                if cleaned and len(cleaned) > 20:
                                    paragraphs.append(cleaned)

                # Fallback if no block tags found
                if not paragraphs:
                    raw_all = article_div.get_text(separator="\n\n")
                    for chunk in raw_all.split("\n\n"):
                        text = chunk.strip()
                        if len(text) > 40:
                            cleaned = sanitize_html_text(text)
                            if cleaned and len(cleaned) > 30:
                                paragraphs.append(cleaned)

            full_text = "\n\n".join(paragraphs) if paragraphs else None

            # Fallback if meta description wasn't found but we got paragraphs
            if not excerpt and paragraphs:
                excerpt = paragraphs[0]

            return excerpt, full_text
        except Exception as e:
            logger.debug("Failed parsing article HTML: %s", e)
            return None, None

    async def enrich_item_content(
        self,
        item: ParsedJudgmentItem,
        client: httpx.AsyncClient | None = None,
    ) -> bool:
        """
        Fetches the destination article web page to extract real narrative text and summary
        when RSS feed provides only a headline or empty description (e.g. LiveLaw google_feeds).
        """
        # If item already has substantive text, skip enrichment
        if item.full_text and len(item.full_text.strip()) > 200 and item.excerpt != item.title:
            return False

        if not item.url or not item.url.startswith("http"):
            return False

        should_close = False
        if client is None:
            client = httpx.AsyncClient(timeout=8.0, follow_redirects=True)
            should_close = True

        try:
            headers = {"User-Agent": DEFAULT_USER_AGENT}
            resp = await client.get(item.url, headers=headers)
            if resp.status_code == 200:
                html_text = resp.text
                extracted_excerpt, extracted_full_text = self.extract_article_text_from_html(html_text)
                if extracted_full_text:
                    item.full_text = extracted_full_text
                if extracted_excerpt and extracted_excerpt != item.title:
                    item.excerpt = extracted_excerpt
                elif extracted_full_text and item.excerpt == item.title:
                    paragraphs = [p.strip() for p in extracted_full_text.split("\n\n") if p.strip()]
                    item.excerpt = paragraphs[0] if paragraphs else extracted_full_text[:350]

                # Re-run classifier now that we have rich narrative text
                if extracted_full_text or extracted_excerpt:
                    classification = LegalClassifier.classify(
                        title=item.title,
                        text=item.excerpt or item.title,
                        source=item.source,
                        default_court=CourtInfo(
                            court_code=item.court_code,
                            court_name=item.court_name,
                            court_level=item.court_level,
                        ),
                        url=item.url,
                    )
                    if classification.court:
                        item.court_code = classification.court.court_code
                        item.court_name = classification.court.court_name
                        item.court_level = classification.court.court_level
                    if classification.subject_category:
                        item.subject_category = classification.subject_category
                    if classification.statute_tags:
                        item.tags = list(dict.fromkeys((item.tags or []) + classification.statute_tags))
                    if classification.parties:
                        item.parties = classification.parties

                    c_type, c_conf = classify_content_type(
                        title=item.title,
                        text=item.full_text or item.excerpt,
                        source=item.source,
                        url=item.url,
                    )
                    item.content_type = c_type
                    item.content_type_confidence = c_conf
                    return True
        except Exception as err:
            logger.debug("Failed enriching content for %s: %s", item.url, err)
        finally:
            if should_close:
                await client.aclose()

        return False

    async def enrich_items_content(
        self,
        items: list[ParsedJudgmentItem],
        client: httpx.AsyncClient | None = None,
        max_enrich: int = 35,
    ) -> int:
        """
        Concurrently enriches items missing full text, limited by concurrency semaphore.
        """
        candidates = [
            item for item in items
            if not item.full_text or len(item.full_text.strip()) < 150 or item.excerpt == item.title
        ][:max_enrich]

        if not candidates:
            return 0

        semaphore = asyncio.Semaphore(5)
        should_close = False
        if client is None:
            client = httpx.AsyncClient(timeout=8.0, follow_redirects=True)
            should_close = True

        async def _enrich_with_sem(item: ParsedJudgmentItem) -> bool:
            async with semaphore:
                return await self.enrich_item_content(item, client=client)

        try:
            results = await asyncio.gather(*[_enrich_with_sem(it) for it in candidates], return_exceptions=True)
            enriched_count = sum(1 for r in results if r is True)
            logger.info("Enriched %d / %d legal items with full article text", enriched_count, len(candidates))
            return enriched_count
        finally:
            if should_close:
                await client.aclose()

    async def ingest_source(
        self,
        source_config: FeedSourceConfig,
        client: httpx.AsyncClient | None = None,
    ) -> list[ParsedJudgmentItem]:
        """
        Fetches and parses a single legal feed source with error isolation.
        """
        if not source_config.enabled:
            return []

        logger.info("Ingesting legal feed source: %s (%s)", source_config.name, source_config.url)
        xml_content = await self.fetch_feed_xml(source_config.url, client=client)
        items = self.parse_feed_content(xml_content, source_config)
        logger.info("Parsed %d legal items from source: %s", len(items), source_config.source_id)

        # Enrich items missing full text with live article content
        try:
            await self.enrich_items_content(items, client=client)
        except Exception as enrich_err:
            logger.debug("Enrichment skipped due to error: %s", enrich_err)

        return items

    async def ingest_all(
        self,
        feeds: list[FeedSourceConfig] | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> list[ParsedJudgmentItem]:
        """
        Fetches and processes all configured Indian legal feeds concurrently.
        Isolates errors per feed so failure in one source does not crash the pipeline.
        """
        feed_list = feeds or DEFAULT_LEGAL_FEEDS
        all_items: list[ParsedJudgmentItem] = []

        should_close = False
        if client is None:
            client = httpx.AsyncClient(timeout=self.timeout, follow_redirects=True)
            should_close = True

        try:
            for feed in feed_list:
                try:
                    items = await self.ingest_source(feed, client=client)
                    all_items.extend(items)
                except Exception:
                    logger.exception(
                        "Gracefully isolated error ingesting feed '%s' (%s)",
                        feed.name,
                        feed.url,
                    )
        finally:
            if should_close:
                await client.aclose()

        return all_items

    @staticmethod
    def _extract_date(entry: Any) -> datetime.date:
        """
        Extracts publication or judgment date from feed entry, defaulting to today.
        """
        time_struct = entry.get("published_parsed") or entry.get("updated_parsed")
        if time_struct:
            try:
                return datetime.date(time_struct.tm_year, time_struct.tm_mon, time_struct.tm_mday)
            except (ValueError, TypeError, OverflowError):
                logger.debug("Failed parsing struct_time %s, using current UTC date", time_struct)

        return datetime.datetime.now(datetime.UTC).date()
