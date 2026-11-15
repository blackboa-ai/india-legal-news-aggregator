"""
Phase 1 Unit Tests: RSS Ingestion Pipeline, Deduplication & Legal Classifier
India Legal News Aggregator - Free-Tier Architecture (< 250 MB RAM)
"""

import asyncio
import datetime
from unittest.mock import AsyncMock, patch

import pytest
from app.services.legal_classifier import (
    CANONICAL_CATEGORIES,
    LegalClassifier,
)
from app.services.rss_ingestor import (
    FeedSourceConfig,
    ParsedJudgmentItem,
    RSSIngestor,
    canonicalize_url,
    compute_external_id,
    sanitize_html_text,
)
from app.workers.ingestion_worker import IngestionWorker

# ==============================================================================
# Sample Indian Legal RSS / Atom XML Fixtures
# ==============================================================================

SAMPLE_INDIAN_KANOON_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Indian Kanoon - Recent Judgments</title>
    <link>https://indiankanoon.org/feeds/latest/</link>
    <description>Recent legal judgments from Indian courts</description>
    <item>
      <title>Arvind Kejriwal vs Directorate Of Enforcement on 12 July, 2024</title>
      <link>https://indiankanoon.org/doc/12345678/?utm_source=feed&amp;utm_medium=rss</link>
      <description><![CDATA[
        <p>The Supreme Court of India granted interim bail to the petitioner in connection with excise policy case under <b>Section 438 CrPC</b> and <b>Article 21</b> of the Constitution. Citation: 2024 INSC 512.</p>
      ]]></description>
      <pubDate>Fri, 12 Jul 2024 10:30:00 GMT</pubDate>
    </item>
    <item>
      <title>State Of Maharashtra v. Union Of India</title>
      <link>https://indiankanoon.org/doc/87654321/</link>
      <description><![CDATA[
        The 5-judge Constitution Bench interpreted Article 32 and federalism principles regarding legislative competence and the basic structure doctrine. (2024) 3 SCC 450.
      ]]></description>
      <pubDate>Mon, 15 Jul 2024 14:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>
"""

SAMPLE_LIVELAW_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>LiveLaw - Supreme Court and High Courts</title>
    <link>https://www.livelaw.in/rss/feed.xml</link>
    <item>
      <title>High Court of Delhi Reaffirms Power Under Section 482 BNSS To Quash Criminal Proceedings</title>
      <link>https://www.livelaw.in/high-court/delhi-high-court/section-482-bnss-quashing-fir-delhi-hc-254123?utm_campaign=daily_digest</link>
      <description><![CDATA[
        <p><b>New Delhi:</b> High Court of Delhi held that inherent powers under Section 482 BNSS (corresponding to Section 482 CrPC) must be exercised to prevent abuse of process. Section 103 BNS murder charges quashed. 2024 DHC 3410.</p>
        <script>alert('malicious')</script>
      ]]></description>
      <pubDate>Tue, 16 Jul 2024 08:15:00 GMT</pubDate>
    </item>
    <item>
      <title>Cheque Bounce: Section 138 NI Act Offence Compoundable Even At Appellate Stage, Holds High Court of Bombay</title>
      <link>https://www.livelaw.in/high-court/bombay-high-court/ni-act-section-138-compounding-bombay-hc-254999/</link>
      <description><![CDATA[
        High Court of Bombay permitted compounding of cheque dishonour complaint under Section 138 of Negotiable Instruments Act upon deposit of settlement sum.
      ]]></description>
      <pubDate>Wed, 17 Jul 2024 11:45:00 GMT</pubDate>
    </item>
  </channel>
</rss>
"""

SAMPLE_BAR_AND_BENCH_XML = """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0">
  <channel>
    <title>Bar and Bench - Legal News</title>
    <link>https://www.barandbench.com/</link>
    <item>
      <title>National Company Law Appellate Tribunal: Section 7 IBC Petition Admissible Once Debt and Default Established</title>
      <link>https://www.barandbench.com/news/corporate/nclat-section-7-ibc-admission</link>
      <description><![CDATA[
        The NCLAT held that under Insolvency and Bankruptcy Code (IBC), the corporate insolvency resolution process (CIRP) must be initiated once default exceeds statutory threshold.
      ]]></description>
      <pubDate>Thu, 18 Jul 2024 16:20:00 GMT</pubDate>
    </item>
  </channel>
</rss>
"""


# ==============================================================================
# 1. HTML Sanitization & Whitespace Normalization Tests
# ==============================================================================

class TestHTMLSanitization:
    """Tests HTML tag stripping, script removal, and whitespace normalization."""

    def test_strip_basic_html_tags(self):
        raw = "<p>The <b>Supreme Court</b> issued notice in the <i>writ petition</i>.</p>"
        cleaned = sanitize_html_text(raw)
        assert cleaned == "The Supreme Court issued notice in the writ petition."

    def test_strip_scripts_styles_and_iframes(self):
        raw = """
        <div>
            <script type="text/javascript">var secret = 123;</script>
            <style>p { color: red; }</style>
            <h1>Judgment Summary</h1>
            <p>Court dismissed appeal under Section 302 IPC.</p>
            <iframe src="https://tracker.com"></iframe>
        </div>
        """
        cleaned = sanitize_html_text(raw)
        assert "secret" not in cleaned
        assert "color: red" not in cleaned
        assert "<iframe" not in cleaned
        assert cleaned == "Judgment Summary Court dismissed appeal under Section 302 IPC."

    def test_unescape_html_entities(self):
        raw = "Petitioner&#39;s rights under Article 21 &amp; Article 14 were &quot;violated&quot; &nbsp; "
        cleaned = sanitize_html_text(raw)
        assert cleaned == 'Petitioner\'s rights under Article 21 & Article 14 were "violated"'

    def test_normalize_whitespace_and_newlines(self):
        raw = "  Order   VII\n\n\t  Rule   11 \r\n  CPC   dismissal.  "
        cleaned = sanitize_html_text(raw)
        assert cleaned == "Order VII Rule 11 CPC dismissal."

    def test_empty_or_none_input(self):
        assert sanitize_html_text(None) == ""
        assert sanitize_html_text("") == ""
        assert sanitize_html_text("   \n\t  ") == ""


# ==============================================================================
# 2. Canonical URL & SHA-256 Deduplication Tests
# ==============================================================================

class TestDeduplication:
    """Tests URL canonicalization and deterministic SHA-256 external_id hashing."""

    def test_canonicalize_url_strips_tracking_params(self):
        url1 = "https://www.livelaw.in/news/bail-order-123?utm_source=twitter&utm_medium=social&utm_campaign=breaking"
        url2 = "https://www.livelaw.in/news/bail-order-123"
        assert canonicalize_url(url1) == "https://www.livelaw.in/news/bail-order-123"
        assert canonicalize_url(url2) == "https://www.livelaw.in/news/bail-order-123"

    def test_canonicalize_url_handles_trailing_slashes(self):
        url1 = "https://indiankanoon.org/doc/123456/"
        url2 = "https://indiankanoon.org/doc/123456"
        assert canonicalize_url(url1) == canonicalize_url(url2)

    def test_deterministic_external_id(self):
        url = "https://indiankanoon.org/doc/55555/?utm_source=rss"
        title = "ABC Ltd. vs Union of India"

        id1 = compute_external_id(url, title)
        id2 = compute_external_id("https://indiankanoon.org/doc/55555/", "  abc ltd. vs union of india  ")

        assert len(id1) == 64  # SHA-256 hex digest length
        assert id1 == id2  # Case-insensitive title and normalized URL match

    def test_distinct_external_ids_for_different_items(self):
        id1 = compute_external_id("https://sci.gov.in/order/1", "Order 1")
        id2 = compute_external_id("https://sci.gov.in/order/2", "Order 2")
        id3 = compute_external_id("https://sci.gov.in/order/1", "Order 2")

        assert id1 != id2
        assert id1 != id3
        assert id2 != id3


# ==============================================================================
# 3. Lightweight Legal Classifier Tests (< 50 MB RAM)
# ==============================================================================

class TestLegalClassifier:
    """Tests classification across Indian legal domains, statutes, citations, and courts."""

    def test_canonical_categories_defined(self):
        assert len(CANONICAL_CATEGORIES) == 10
        assert "Constitutional" in CANONICAL_CATEGORIES
        assert "Criminal" in CANONICAL_CATEGORIES
        assert "Corporate" in CANONICAL_CATEGORIES
        assert "Civil" in CANONICAL_CATEGORIES

    def test_criminal_domain_classification(self):
        title = "State of Punjab v. Baldev Singh"
        text = "The High Court granted anticipatory bail under Section 438 CrPC in FIR registered under Section 302 IPC for murder."
        result = LegalClassifier.classify(title, text)

        assert result.subject_category == "Criminal"
        assert result.confidence >= 0.75
        assert any("438" in tag for tag in result.statute_tags)
        assert any("302" in tag for tag in result.statute_tags)

    def test_bns_bnss_new_criminal_laws(self):
        title = "Ramesh Kumar vs State of NCT of Delhi"
        text = "Petition filed under Section 482 BNSS seeking quashing of charge under Section 103 BNS."
        result = LegalClassifier.classify(title, text)

        assert result.subject_category == "Criminal"
        assert any("BNSS" in tag for tag in result.statute_tags)
        assert any("BNS" in tag for tag in result.statute_tags)

    def test_constitutional_domain_classification(self):
        title = "Justice K.S. Puttaswamy (Retd.) v. Union of India"
        text = "The 9-judge Constitution Bench held that the right to privacy is protected under Article 21, Article 14, and Article 19 as fundamental rights."
        result = LegalClassifier.classify(title, text)

        assert result.subject_category == "Constitutional"
        assert result.confidence >= 0.80
        assert any("Article 21" in tag for tag in result.statute_tags)
        assert any("Article 14" in tag for tag in result.statute_tags)

    def test_corporate_and_ibc_classification(self):
        title = "State Bank of India v. Videocon Industries Ltd."
        text = "NCLAT admitted Section 7 IBC petition initiating Corporate Insolvency Resolution Process (CIRP) against the corporate debtor."
        result = LegalClassifier.classify(title, text)

        assert result.subject_category == "Corporate"
        assert any("IBC" in tag for tag in result.statute_tags)

    def test_civil_cpc_classification(self):
        title = "Rameshwar Dayal v. Jagdish Prasad"
        text = "Application under Order VII Rule 11 CPC for rejection of plaint in a suit for permanent injunction and specific performance."
        result = LegalClassifier.classify(title, text)

        assert result.subject_category == "Civil"
        assert any("Order" in tag and "Rule" in tag for tag in result.statute_tags)

    def test_family_law_classification(self):
        title = "Sunita Sharma v. Rajesh Sharma"
        text = "Petition under Section 13(1) Hindu Marriage Act for divorce and maintenance under Section 125 CrPC."
        result = LegalClassifier.classify(title, text)

        assert result.subject_category == "Family"
        assert any("Hindu Marriage" in tag for tag in result.statute_tags)

    def test_environment_classification(self):
        title = "Vardhaman Kaushik v. Union of India"
        text = "National Green Tribunal (NGT) issued directions to curb air pollution and stubble burning under Environment Protection Act."
        result = LegalClassifier.classify(title, text)

        assert result.subject_category == "Environment"

    def test_labour_classification(self):
        title = "Workmen of Dimakuchi Tea Estate v. Management"
        text = "Industrial tribunal award regarding retrenchment and gratuity under Industrial Disputes Act."
        result = LegalClassifier.classify(title, text)

        assert result.subject_category == "Labour"

    def test_education_classification(self):
        title = "NEET Aspirants Association v. National Testing Agency"
        text = "Plea challenging NEET examination grace marks and college admission seat allocation."
        result = LegalClassifier.classify(title, text)

        assert result.subject_category == "Education"

    def test_ni_act_statutory_extraction(self):
        title = "M/s ABC Enterprises v. XYZ Pvt Ltd"
        text = "Complaint for cheque bounce dishonour under Section 138 NI Act."
        result = LegalClassifier.classify(title, text)

        assert any("138 NI Act" in tag for tag in result.statute_tags)

    def test_citation_extraction(self):
        text = "As held in 2024 INSC 512, following (2023) 4 SCC 120 and AIR 2022 SC 101 in Criminal Appeal No. 450/2023."
        citations = LegalClassifier.extract_citations(text)

        assert any("2024 INSC 512" in c for c in citations)
        assert any("(2023) 4 SCC 120" in c for c in citations)
        assert any("AIR 2022 SC 101" in c for c in citations)
        assert any("Criminal Appeal" in c for c in citations)

    def test_court_extraction(self):
        sc_court = LegalClassifier.extract_court("Supreme Court of India delivered the verdict.")
        assert sc_court.court_code == "sc"
        assert sc_court.court_level == 1

        delhi_court = LegalClassifier.extract_court("High Court of Delhi heard the bail plea.")
        assert delhi_court.court_code == "delhi-hc"
        assert delhi_court.court_level == 2

        nclat_court = LegalClassifier.extract_court("NCLAT upheld the order.")
        assert nclat_court.court_code == "nclat"
        assert nclat_court.court_level == 3

    def test_party_extraction(self):
        parties1 = LegalClassifier.extract_parties("Arvind Kejriwal v. Directorate of Enforcement")
        assert len(parties1) == 2
        assert parties1[0]["name"] == "Arvind Kejriwal"
        assert parties1[1]["name"] == "Directorate of Enforcement"

        parties2 = LegalClassifier.extract_parties("State of Maharashtra vs XYZ Corporation Ltd. - Bail Order")
        assert len(parties2) == 2
        assert parties2[0]["name"] == "State of Maharashtra"
        assert "XYZ Corporation" in parties2[1]["name"]


# ==============================================================================
# 4. Mocked Feed Ingestion & Parsing Tests
# ==============================================================================

class TestFeedIngestion:
    """Tests parsing of RSS and Atom feeds with fixture data."""

    def test_parse_indian_kanoon_xml(self):
        ingestor = RSSIngestor()
        source = FeedSourceConfig(
            source_id="indiankanoon",
            name="Indian Kanoon",
            url="https://indiankanoon.org/feeds/latest/",
        )
        items = ingestor.parse_feed_content(SAMPLE_INDIAN_KANOON_XML, source)

        assert len(items) == 2

        item1 = items[0]
        assert "Arvind Kejriwal" in item1.title
        assert item1.source == "indiankanoon"
        assert item1.subject_category == "Criminal"
        assert len(item1.external_id) == 64
        assert "Article 21" in item1.tags or "Section 438 CrPC" in item1.tags
        assert item1.judgment_date == datetime.date(2024, 7, 12)

        item2 = items[1]
        assert item2.subject_category == "Constitutional"
        assert item2.judgment_date == datetime.date(2024, 7, 15)

    def test_parse_livelaw_xml(self):
        ingestor = RSSIngestor()
        source = FeedSourceConfig(
            source_id="livelaw",
            name="LiveLaw",
            url="https://www.livelaw.in/rss/feed.xml",
        )
        items = ingestor.parse_feed_content(SAMPLE_LIVELAW_XML, source)

        assert len(items) == 2

        item1 = items[0]
        assert "482 BNSS" in item1.title
        assert item1.court_code == "delhi-hc"
        assert item1.court_level == 2
        # Verify script tag was stripped from excerpt
        assert "<script>" not in item1.excerpt
        assert "alert(" not in item1.excerpt

        item2 = items[1]
        assert "138 NI Act" in item2.title
        assert item2.court_code == "bombay-hc"

    def test_parse_bar_and_bench_xml(self):
        ingestor = RSSIngestor()
        source = FeedSourceConfig(
            source_id="barandbench",
            name="Bar & Bench",
            url="https://www.barandbench.com/feed",
        )
        items = ingestor.parse_feed_content(SAMPLE_BAR_AND_BENCH_XML, source)

        assert len(items) == 1
        item = items[0]
        assert item.subject_category == "Corporate"
        assert item.court_code == "nclat"
        assert item.court_level == 3


# ==============================================================================
# 5. Database Deduplication & Worker Isolation Tests
# ==============================================================================

class TestIngestionWorker:
    """Tests worker deduplication logic, per-feed error isolation, and graceful shutdown."""

    @pytest.mark.asyncio
    async def test_persist_item_skips_duplicate(self):
        worker = IngestionWorker()
        mock_session = AsyncMock()

        # Simulate first check: does not exist -> persists
        with patch.object(worker, "check_exists", AsyncMock(side_effect=[False, True])):
            item = ParsedJudgmentItem(
                external_id="abc123sha256hash",
                title="Test Judgment v. Union of India",
                short_title="Test Judgment",
                court_code="sc",
                court_name="Supreme Court of India",
                court_level=1,
                judgment_date=datetime.date(2024, 7, 1),
                subject_category="Constitutional",
                excerpt="Test summary",
                full_text=None,
                url="https://sci.gov.in/test/1",
                parties=[{"role": "petitioner", "name": "Test"}],
                tags=["Article 21"],
                source="sci",
                classification_confidence=0.92,
            )

            # First insertion: should succeed
            inserted1 = await worker.persist_item(mock_session, item)
            assert inserted1 is True
            assert mock_session.add.call_count == 1

            # Second insertion: duplicate external_id -> should skip
            inserted2 = await worker.persist_item(mock_session, item)
            assert inserted2 is False
            assert mock_session.add.call_count == 1  # Not called again

    @pytest.mark.asyncio
    async def test_feed_error_isolation(self):
        """Failure in feed 1 should not halt processing of feed 2."""
        worker = IngestionWorker()
        mock_session = AsyncMock()

        feed_good = FeedSourceConfig(
            source_id="sci",
            name="Good Feed",
            url="https://sci.gov.in/good.xml",
        )
        feed_bad = FeedSourceConfig(
            source_id="broken",
            name="Broken Feed",
            url="https://broken.domain/error.xml",
        )
        worker.feeds = [feed_bad, feed_good]

        # Ingestor raises on bad feed, succeeds on good feed
        async def mock_ingest(config, **kwargs):
            if config.source_id == "broken":
                raise ConnectionError("Network unreachable")
            return [
                ParsedJudgmentItem(
                    external_id="valid_hash_123",
                    title="Good Title v. State",
                    short_title="Good Title",
                    court_code="sc",
                    court_name="Supreme Court of India",
                    court_level=1,
                    judgment_date=datetime.date(2024, 7, 1),
                    subject_category="Criminal",
                    excerpt="Valid excerpt",
                    full_text=None,
                    url="https://sci.gov.in/item1",
                    parties=[],
                    tags=["Section 438 CrPC"],
                    source="sci",
                    classification_confidence=0.88,
                )
            ]

        with (
            patch.object(worker.ingestor, "ingest_source", side_effect=mock_ingest),
            patch.object(worker, "check_exists", AsyncMock(return_value=False)),
        ):
            report = await worker.run_once(session=mock_session)

            assert report.failed_sources == 1
            assert report.total_inserted == 1
            assert report.total_fetched == 1
            assert len(report.sources_reports) == 2
            assert report.sources_reports[0]["error"] is not None
            assert report.sources_reports[1]["items_inserted"] == 1

    @pytest.mark.asyncio
    async def test_graceful_shutdown(self):
        """Worker loop terminates cleanly when stop() is signaled."""
        worker = IngestionWorker(interval_seconds=100)

        # Mock run_once to avoid real network/DB calls
        with patch.object(worker, "run_once", AsyncMock()):
            task = worker.start()
            assert worker.is_running is True

            # Allow loop to start and pause
            await asyncio.sleep(0.05)

            # Signal shutdown
            worker.stop()
            await asyncio.wait_for(task, timeout=2.0)

            assert worker.is_running is False
            assert task.done()
