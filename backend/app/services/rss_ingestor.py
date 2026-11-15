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

from app.services.legal_classifier import CourtInfo, LegalClassifier

logger = logging.getLogger(__name__)

# Polite crawler User-Agent adhering to Indian court & legal publication etiquette
DEFAULT_USER_AGENT = (
    "IndiaLegalNewsAggregator/2.0 "
    "(+https://github.com/blackboa-ai/india-legal-news-aggregator; legal-research-bot)"
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


# Pre-configured legal sources covering Supreme Court, Kanoon, LiveLaw, Bar & Bench
DEFAULT_LEGAL_FEEDS: list[FeedSourceConfig] = [
    FeedSourceConfig(
        source_id="sci",
        name="Supreme Court of India Judgments",
        url="https://main.sci.gov.in/rss/judgments.xml",
        default_court_code="sc",
        default_court_name="Supreme Court of India",
        default_court_level=1,
    ),
    FeedSourceConfig(
        source_id="indiankanoon",
        name="Indian Kanoon Recent Judgments",
        url="https://indiankanoon.org/feeds/latest/",
        default_court_code="sc",
        default_court_name="Supreme Court of India",
        default_court_level=1,
    ),
    FeedSourceConfig(
        source_id="livelaw",
        name="LiveLaw Legal News & Judgments",
        url="https://www.livelaw.in/rss/feed.xml",
        default_court_code="sc",
        default_court_name="Supreme Court of India",
        default_court_level=1,
    ),
    FeedSourceConfig(
        source_id="barandbench",
        name="Bar & Bench Legal News",
        url="https://www.barandbench.com/feed",
        default_court_code="sc",
        default_court_name="Supreme Court of India",
        default_court_level=1,
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

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def sanitize_html_text(raw_html: str | None) -> str:
    """
    Safely strips HTML tags, script/style blocks, and unescapes entities.
    Normalizes excessive whitespace into single spaces.
    """
    if not raw_html:
        return ""

    try:
        soup = BeautifulSoup(raw_html, "html.parser")
        # Remove active or formatting markup tags
        for element in soup(["script", "style", "noscript", "iframe", "header", "footer", "nav", "aside"]):
            element.decompose()

        text = soup.get_text(separator=" ")
    except (ValueError, TypeError, AttributeError):
        # Fallback regex tag stripping in case of malformed markup
        text = re.sub(r"<[^>]+>", " ", raw_html)

    # Unescape HTML entities (&nbsp;, &amp;, &#39;, etc.)
    text = html.unescape(text)
    # Normalize non-breaking spaces and whitespace
    text = text.replace("\xa0", " ").replace("\u200b", "")
    # Remove space before punctuation marks (. , : ; ? !)
    text = re.sub(r"\s+([,.:;?!])", r"\1", text)
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
            "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
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

            # Excerpt extraction & cleaning
            raw_summary = (
                entry.get("summary")
                or entry.get("description")
                or (entry.get("content", [{}])[0].get("value") if entry.get("content") else "")
                or ""
            )
            excerpt = sanitize_html_text(raw_summary)

            # Extract full text if provided in content payload
            full_text = None
            if entry.get("content"):
                candidate_content = sanitize_html_text(entry.content[0].get("value", ""))
                if len(candidate_content) > len(excerpt):
                    full_text = candidate_content

            # Parse judgment or publication date
            judgment_date = self._extract_date(entry)

            # Run deterministic legal classification and metadata extraction
            classification = LegalClassifier.classify(
                title=title,
                text=excerpt,
                source=source_config.source_id,
                default_court=default_court,
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
            )
            items.append(item)

        return items

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
