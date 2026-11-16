"""
Unit & Integration Tests: Content Classification Engine & RSS Ingestion (v2.1 Phase 1)
Tests the 3-state classification system ('judgment', 'news', 'unknown') across
authoritative source rules, syntactic judicial markers, journalistic signals,
conflict resolution, schema validation, and end-to-end RSS ingestion.
"""

import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from app.models.judgment import Judgment
from app.schemas.judgment import JudgmentListItem, JudgmentResponse, SearchResultItem
from app.services.legal_classifier import (
    ClassificationResult,
    LegalClassifier,
    classify_content_type,
)
from app.services.rss_ingestor import (
    FeedSourceConfig,
    ParsedJudgmentItem,
    RSSIngestor,
)
from app.workers.ingestion_worker import IngestionWorker


# ==============================================================================
# 1. Rule A: Authoritative Source & Route Tests
# ==============================================================================

class TestRuleASourceClassification:
    """Tests that SCI and Indian Kanoon articles are authoritative judgments."""

    def test_sci_source_always_judgment(self):
        """SCI articles must always be classified as 'judgment' with 1.0 confidence."""
        content_type, confidence = classify_content_type(
            title="Supreme Court Collegium Recommends Transfer of Judges",
            text="Union cabinet approved and law minister told reporters on Monday.",
            source="sci",
            url="https://main.sci.gov.in/rss/123",
        )
        assert content_type == "judgment"
        assert confidence == 1.0

    def test_indiankanoon_source_always_judgment(self):
        """Indian Kanoon articles must always be classified as 'judgment' with 1.0 confidence."""
        content_type, confidence = classify_content_type(
            title="General News Update on Court Proceedings",
            text="Some brief notes on judicial reforms.",
            source="indiankanoon",
            url="https://indiankanoon.org/doc/45678/",
        )
        assert content_type == "judgment"
        assert confidence == 1.0

    def test_source_case_insensitivity(self):
        """Source parameter matches case-insensitively with leading/trailing whitespace."""
        assert classify_content_type("Case 1", source=" SCI ") == ("judgment", 1.0)
        assert classify_content_type("Case 2", source="IndianKanoon") == ("judgment", 1.0)
        assert classify_content_type("Case 3", source="INDIANKANOON") == ("judgment", 1.0)

    def test_url_route_biases(self):
        """Verify URL route patterns bias scoring toward news or judgment candidates."""
        # News path bias
        ct_news, conf_news = classify_content_type(
            title="Legal Sector Roundup",
            text="Discussion on market trends and law practice.",
            source="barandbench",
            url="https://www.barandbench.com/news/legal-sector-roundup",
        )
        assert ct_news == "news"
        assert conf_news >= 0.65

        ct_interview, _ = classify_content_type(
            title="Perspective on Judicial Reforms",
            text="A conversation with senior advocates.",
            source="livelaw",
            url="https://www.livelaw.in/interviews/reforms-perspective",
        )
        assert ct_interview == "news"

        # Judgment path bias
        ct_order, conf_order = classify_content_type(
            title="Directions Issued on Civic Amenities",
            text="Competent authorities directed to comply within 4 weeks.",
            source="livelaw",
            url="https://www.livelaw.in/orders/delhi-civic-amenities-order",
        )
        assert ct_order == "judgment"
        assert conf_order >= 0.65


# ==============================================================================
# 2. Rule B: LiveLaw / Bar & Bench Judicial Markers Tests
# ==============================================================================

class TestLiveLawBarAndBenchJudgments:
    """Tests bail orders, quashing orders, and dispositive judicial markers."""

    def test_livelaw_bail_granted_order(self):
        """LiveLaw bail orders with [Read Order] must be classified as 'judgment'."""
        title = "Delhi High Court Grants Bail to Accused in Excise Policy Case [Read Order]"
        text = "Justice Sharma observed that petitioner has been in custody for 14 months. Bail granted on bond."
        content_type, confidence = classify_content_type(
            title=title,
            text=text,
            source="livelaw",
            url="https://www.livelaw.in/news-updates/delhi-hc-grants-bail-excise-policy",
        )
        assert content_type == "judgment"
        assert confidence >= 0.70

    def test_anticipatory_bail_order(self):
        """Anticipatory bail grant/denial orders are classified as 'judgment'."""
        title = "Sessions Court Rejects Anticipatory Bail Plea in Cheating Case"
        text = "The court observed that custodial interrogation is necessary. Anticipatory bail rejected."
        content_type, confidence = classify_content_type(
            title=title,
            text=text,
            source="barandbench",
            url="https://www.barandbench.com/orders/sessions-court-rejects-bail",
        )
        assert content_type == "judgment"
        assert confidence >= 0.70

    def test_quashing_order_section_482(self):
        """Section 482 CrPC FIR quashing orders must be classified as 'judgment'."""
        title = "Section 482 CrPC: High Court Quashes FIR Against Man in Matrimonial Dispute"
        text = "Finding no prima facie case, the High Court quashed the FIR and consequential proceedings."
        content_type, confidence = classify_content_type(
            title=title,
            text=text,
            source="barandbench",
            url="https://www.barandbench.com/orders/hc-quashes-fir-482-crpc",
        )
        assert content_type == "judgment"
        assert confidence >= 0.70

    def test_quashing_chargesheet(self):
        """Chargesheet quashing is classified as 'judgment'."""
        title = "High Court Quashes Chargesheet in Fraud Case v. State"
        text = "Coram: Hon'ble Mr. Justice Rao. The bench held that civil dispute cannot be criminalized."
        content_type, confidence = classify_content_type(
            title=title,
            text=text,
            source="livelaw",
            url="https://www.livelaw.in/judgment-summary/chargesheet-quashed",
        )
        assert content_type == "judgment"
        assert confidence >= 0.70

    def test_conviction_upheld_and_appeal_dismissed(self):
        """Dispositive verbs 'conviction upheld' and 'appeal dismissed' classify as 'judgment'."""
        title = "Conviction Upheld in Murder Appeal: High Court Dismisses Plea"
        text = "The Division Bench found eyewitness testimony credible and confirmed the conviction."
        content_type, confidence = classify_content_type(
            title=title,
            text=text,
            source="livelaw",
            url="https://www.livelaw.in/news-updates/conviction-upheld-murder",
        )
        assert content_type == "judgment"
        assert confidence >= 0.70

    def test_syntactic_bench_markers_and_case_numbers(self):
        """Coram, Hon'ble Justice, SLP, and Writ Petition markers classify as 'judgment'."""
        title = "SLP(Crl) No. 4321/2024: State of Maharashtra vs Ramesh Kumar"
        text = "Coram: Hon'ble Mr. Justice Khanna and Hon'ble Ms. Justice Trivedi. Disposed of."
        content_type, confidence = classify_content_type(
            title=title,
            text=text,
            source="livelaw",
            url="https://www.livelaw.in/orders/slp-crl-4321-2024",
        )
        assert content_type == "judgment"
        assert confidence >= 0.75

    def test_in_re_case_marker(self):
        """'In re:' suo motu title marker classifies as 'judgment'."""
        title = "In re: Assessment of Measures for Protecting Prisoner Rights"
        text = "Writ petition disposed of with binding guidelines issued to state authorities."
        content_type, confidence = classify_content_type(
            title=title,
            text=text,
            source="barandbench",
            url="https://www.barandbench.com/orders/in-re-prisoner-rights",
        )
        assert content_type == "judgment"
        assert confidence >= 0.70


# ==============================================================================
# 3. Rule C: LiveLaw / Bar & Bench News Markers Tests
# ==============================================================================

class TestLiveLawBarAndBenchNews:
    """Tests collegium, appointment, cabinet, and journalistic reporting markers."""

    def test_collegium_recommendation_news(self):
        """Collegium elevation recommendations must be classified as 'news'."""
        title = "Supreme Court Collegium Recommends 5 Names for Elevation to High Courts"
        text = "The Supreme Court Collegium headed by the Chief Justice met on Monday to finalize names."
        content_type, confidence = classify_content_type(
            title=title,
            text=text,
            source="livelaw",
            url="https://www.livelaw.in/news-updates/sc-collegium-recommends-5-names",
        )
        assert content_type == "news"
        assert confidence >= 0.70

    def test_judicial_appointment_and_oath_news(self):
        """Appointment and oath ceremonies must be classified as 'news'."""
        title = "Justice Sanjiv Sharma Appointed as Acting Chief Justice; Takes Oath of Office"
        text = "The ceremony was attended by judges and members of the bar association."
        content_type, confidence = classify_content_type(
            title=title,
            text=text,
            source="barandbench",
            url="https://www.barandbench.com/news/justice-sharma-appointed-acting-cj",
        )
        assert content_type == "news"
        assert confidence >= 0.70

    def test_cabinet_approval_and_reporters_news(self):
        """Cabinet approval and reported statements classify as 'news'."""
        title = "Union Cabinet Approves Mediation Bill 2023; Law Minister Told Reporters on Monday"
        text = "The press release stated that the new legislation aims to reduce court pendency."
        content_type, confidence = classify_content_type(
            title=title,
            text=text,
            source="barandbench",
            url="https://www.barandbench.com/news/cabinet-approves-mediation-bill",
        )
        assert content_type == "news"
        assert confidence >= 0.75

    def test_bar_council_election_news(self):
        """Bar council elections and resolutions classify as 'news'."""
        title = "Bar Council Election Results Declared; Counting Reported on Friday"
        text = "Senior advocates were elected to key positions in the state bar association."
        content_type, confidence = classify_content_type(
            title=title,
            text=text,
            source="livelaw",
            url="https://www.livelaw.in/news-updates/bar-council-election-results",
        )
        assert content_type == "news"
        assert confidence >= 0.70

    def test_symposium_and_lecture_news(self):
        """Conferences, book launches, and lectures classify as 'news'."""
        title = "Former Chief Justice Inaugurates Annual Lecture on Constitutional Law"
        text = "The symposium was organized by the law faculty and brought together legal scholars."
        content_type, confidence = classify_content_type(
            title=title,
            text=text,
            source="livelaw",
            url="https://www.livelaw.in/columns/annual-lecture-constitutional-law",
        )
        assert content_type == "news"
        assert confidence >= 0.70


# ==============================================================================
# 4. Rule D: Ambiguity, Conflict & Unknown Fallback Tests
# ==============================================================================

class TestAmbiguousAndFallbackUnknown:
    """Tests ambiguous snippets, signal conflict resolution, and threshold fallbacks."""

    def test_short_ambiguous_snippet_falls_back_to_unknown(self):
        """Vague or short snippets without markers must cleanly fall back to 'unknown'."""
        content_type, confidence = classify_content_type(
            title="Legal Digest Update",
            text="Routine morning session held.",
            source="livelaw",
            url="https://www.livelaw.in/daily/update-123",
        )
        assert content_type == "unknown"
        assert confidence == 0.5

    def test_empty_inputs_safe(self):
        """Empty or None inputs cleanly return ('unknown', 0.5) without exceptions."""
        ct1, conf1 = classify_content_type("", "", "", "")
        assert ct1 == "unknown"
        assert conf1 == 0.5

        ct2, conf2 = classify_content_type(None, None, None, None)
        assert ct2 == "unknown"
        assert conf2 == 0.5

    def test_conflicting_signals_fall_back_to_unknown(self):
        """When judicial and news markers heavily collide, result must be 'unknown'."""
        title = "Collegium Recommends Judge as Bail Granted in State v. Kumar [Read Order] Reported on Monday"
        text = "Union cabinet approved resolution while high court quashed chargesheet."
        content_type, confidence = classify_content_type(
            title=title,
            text=text,
            source="livelaw",
            url="https://www.livelaw.in/general/conflict-update",
        )
        assert content_type == "unknown"
        assert confidence == 0.5

    def test_low_confidence_threshold_enforced(self):
        """Scores yielding confidence < 0.65 are clamped to 'unknown'."""
        # A single weak marker in text without title reinforcement
        ct, conf = classify_content_type(
            title="General Article",
            text="Reference made in passing without dispositive verbs.",
            source="livelaw",
            url="https://www.livelaw.in/story/100",
        )
        assert ct == "unknown"
        assert conf <= 0.65


# ==============================================================================
# 5. End-to-End RSS Ingestion Tests
# ==============================================================================

class TestEndToEndRSSIngestion:
    """Tests classification during XML parsing and database persistence."""

    def test_rss_ingestor_parses_content_type(self):
        """RSSIngestor must populate content_type and content_type_confidence on ParsedJudgmentItem."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
          <channel>
            <title>Legal Feeds</title>
            <link>https://example.com</link>
            <item>
              <title>Delhi High Court Grants Bail to Accused in Cheating Case [Read Order]</title>
              <link>https://www.livelaw.in/orders/delhi-hc-grants-bail</link>
              <description>Justice Verma granted regular bail under Section 439 CrPC.</description>
              <pubDate>Mon, 15 Jul 2024 10:00:00 GMT</pubDate>
            </item>
            <item>
              <title>Supreme Court Collegium Recommends 3 Judges for High Court</title>
              <link>https://www.barandbench.com/news/collegium-recommends-judges</link>
              <description>The decision was taken in a meeting held on Monday, sources told reporters.</description>
              <pubDate>Mon, 15 Jul 2024 12:00:00 GMT</pubDate>
            </item>
          </channel>
        </rss>
        """
        ingestor = RSSIngestor()
        config = FeedSourceConfig(
            source_id="livelaw",
            name="LiveLaw Feed",
            url="https://www.livelaw.in/feed.xml",
        )
        items = ingestor.parse_feed_content(xml_content, config)
        assert len(items) == 2

        # Item 1: Bail order -> judgment
        assert items[0].content_type == "judgment"
        assert items[0].content_type_confidence >= 0.70

        # Item 2: Collegium news -> news
        assert items[1].content_type == "news"
        assert items[1].content_type_confidence >= 0.70

    def test_rss_ingestor_indiankanoon_always_judgment(self):
        """RSS feed items from Indian Kanoon are always tagged 'judgment' with 1.0 confidence."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
          <channel>
            <title>Indian Kanoon</title>
            <link>https://indiankanoon.org</link>
            <item>
              <title>State of Karnataka v. ABC Ltd</title>
              <link>https://indiankanoon.org/doc/998877/</link>
              <description>Civil appeal on contract enforcement.</description>
              <pubDate>Tue, 16 Jul 2024 10:00:00 GMT</pubDate>
            </item>
          </channel>
        </rss>
        """
        ingestor = RSSIngestor()
        config = FeedSourceConfig(
            source_id="indiankanoon",
            name="Indian Kanoon",
            url="https://indiankanoon.org/feeds/latest/",
        )
        items = ingestor.parse_feed_content(xml_content, config)
        assert len(items) == 1
        assert items[0].content_type == "judgment"
        assert items[0].content_type_confidence == 1.0

    @pytest.mark.asyncio
    async def test_worker_persists_content_type_to_model(self):
        """IngestionWorker.persist_item must store content_type & content_type_confidence on Judgment model."""
        worker = IngestionWorker()
        mock_session = AsyncMock()

        item = ParsedJudgmentItem(
            external_id="test_sha256_hash_1",
            title="Delhi High Court Quashes FIR in Matrimonial Case [Read Order]",
            short_title="Quashing FIR Order",
            court_code="delhi-hc",
            court_name="High Court of Delhi",
            court_level=2,
            judgment_date=datetime.date(2024, 7, 10),
            subject_category="Criminal",
            excerpt="High court quashed FIR under Section 482 CrPC.",
            full_text=None,
            url="https://www.livelaw.in/orders/quashes-fir-1",
            parties=[{"role": "petitioner", "name": "Petitioner"}],
            tags=["Section 482 CrPC"],
            source="livelaw",
            classification_confidence=0.90,
            content_type="judgment",
            content_type_confidence=0.95,
        )

        with patch.object(worker, "check_exists", AsyncMock(return_value=False)):
            with patch("app.workers.ingestion_worker.embedding_service.get_embedding", AsyncMock(return_value=[0.1] * 384)):
                inserted = await worker.persist_item(mock_session, item)
                assert inserted is True
                assert mock_session.add.call_count == 1

                # Inspect persisted Judgment instance
                saved_judgment = mock_session.add.call_args[0][0]
                assert isinstance(saved_judgment, Judgment)
                assert saved_judgment.content_type == "judgment"
                assert saved_judgment.content_type_confidence == 0.95

    @pytest.mark.asyncio
    async def test_worker_fallback_classification_if_unspecified(self):
        """IngestionWorker calls classify_content_type if item lacks content_type."""
        worker = IngestionWorker()
        mock_session = AsyncMock()

        # Item created with default unknown and 0.0 confidence
        item = ParsedJudgmentItem(
            external_id="test_sha256_hash_2",
            title="Supreme Court Collegium Recommends 4 Judges for Elevation",
            short_title="Collegium News",
            court_code="sc",
            court_name="Supreme Court of India",
            court_level=1,
            judgment_date=datetime.date(2024, 7, 10),
            subject_category="Constitutional",
            excerpt="The collegium recommended names after meeting on Monday.",
            full_text=None,
            url="https://www.barandbench.com/news/collegium-recommends-4",
            parties=[],
            tags=[],
            source="barandbench",
            classification_confidence=0.85,
            content_type="unknown",
            content_type_confidence=0.0,
        )

        with patch.object(worker, "check_exists", AsyncMock(return_value=False)):
            with patch("app.workers.ingestion_worker.embedding_service.get_embedding", AsyncMock(return_value=[0.1] * 384)):
                inserted = await worker.persist_item(mock_session, item)
                assert inserted is True

                saved_judgment = mock_session.add.call_args[0][0]
                assert saved_judgment.content_type == "news"
                assert saved_judgment.content_type_confidence >= 0.70


# ==============================================================================
# 6. Database Model & Pydantic Schema Validation Tests
# ==============================================================================

class TestDatabaseModelAndSchemas:
    """Verifies Judgment model attributes, table index, and Pydantic DTOs."""

    def test_judgment_model_columns_and_index(self):
        """Judgment model must declare content_type, content_type_confidence, and index idx_judgments_content_type."""
        table = Judgment.__table__
        assert "content_type" in table.columns
        assert "content_type_confidence" in table.columns
        assert table.columns["content_type"].nullable is False
        assert table.columns["content_type_confidence"].nullable is False

        # Index check
        index_names = {idx.name for idx in table.indexes}
        assert "idx_judgments_content_type" in index_names

    def test_judgment_response_schema_defaults(self):
        """JudgmentResponse schema includes content_type and content_type_confidence with proper defaults."""
        resp = JudgmentResponse(
            id=uuid4(),
            external_id="sha256_test",
            title="Test Case v. State",
            court_code="sc",
            court_name="Supreme Court",
            judgment_date=datetime.date(2024, 1, 1),
            subject_category="Criminal",
            excerpt="Test summary",
            url="https://example.com/test",
            source="livelaw",
            created_at=datetime.datetime.now(datetime.timezone.utc),
            updated_at=datetime.datetime.now(datetime.timezone.utc),
        )
        assert resp.content_type == "unknown"
        assert resp.content_type_confidence == 0.0

    def test_judgment_list_item_schema(self):
        """JudgmentListItem schema includes content_type and content_type_confidence."""
        item = JudgmentListItem(
            id=uuid4(),
            external_id="sha256_list_test",
            title="Test Case v. State",
            court_code="sc",
            court_name="Supreme Court",
            judgment_date=datetime.date(2024, 1, 1),
            subject_category="Criminal",
            excerpt="Test summary",
            url="https://example.com/test",
            source="livelaw",
            content_type="judgment",
            content_type_confidence=0.92,
        )
        assert item.content_type == "judgment"
        assert item.content_type_confidence == 0.92

    def test_search_result_item_schema(self):
        """SearchResultItem schema includes content_type and content_type_confidence."""
        res = SearchResultItem(
            id=uuid4(),
            external_id="sha256_search_test",
            title="Test Search Result v. UOI",
            court_code="sc",
            court_name="Supreme Court",
            court_level=1,
            judgment_date=datetime.date(2024, 1, 1),
            subject_category="Constitutional",
            excerpt="Constitutional law search summary",
            url="https://example.com/test",
            score=0.88,
            content_type="news",
            content_type_confidence=0.75,
        )
        assert res.content_type == "news"
        assert res.content_type_confidence == 0.75
