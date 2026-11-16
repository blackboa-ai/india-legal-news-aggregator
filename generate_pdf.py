import os
import sys
from xml.sax.saxutils import escape
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to compute and render total page count and professional running headers/footers.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, total_pages):
        self.saveState()
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#64748b"))

        # Running Header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(54, 802, "INDIA LEGAL NEWS AGGREGATOR")
            self.setFont("Helvetica", 8)
            self.drawRightString(A4[0] - 54, 802, "v2.1 Master Execution Blueprint & Phased Prompts")
            self.setStrokeColor(colors.HexColor("#cbd5e1"))
            self.setLineWidth(0.5)
            self.line(54, 794, A4[0] - 54, 794)

        # Running Footer (all pages)
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.5)
        self.line(54, 45, A4[0] - 54, 45)
        
        self.setFont("Helvetica", 8)
        self.drawString(54, 32, "Confidential — Legal Tech Free-Tier Production Blueprint (< 250 MB RAM Budget)")
        page_str = f"Page {self._pageNumber} of {total_pages}"
        self.drawRightString(A4[0] - 54, 32, page_str)
        self.restoreState()


def create_execution_plan_pdf(output_path: str):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54,
    )

    styles = getSampleStyleSheet()

    # Color Palette
    c_primary = colors.HexColor("#0f172a")     # Slate 900
    c_secondary = colors.HexColor("#1e293b")   # Slate 800
    c_accent = colors.HexColor("#0284c7")      # Sky 600
    c_emerald = colors.HexColor("#059669")     # Emerald 600
    c_amber = colors.HexColor("#d97706")       # Amber 600
    c_bg_light = colors.HexColor("#f8fafc")    # Slate 50
    c_border = colors.HexColor("#cbd5e1")      # Slate 300
    c_text = colors.HexColor("#334155")        # Slate 700

    # Typography
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=22,
        leading=26,
        textColor=c_primary,
        spaceAfter=4,
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=11,
        leading=15,
        textColor=c_accent,
        spaceAfter=10,
    )

    h1_style = ParagraphStyle(
        'Heading1_Custom',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=17,
        textColor=c_secondary,
        spaceBefore=10,
        spaceAfter=6,
        keepWithNext=True,
    )

    h2_style = ParagraphStyle(
        'Heading2_Custom',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=10.5,
        leading=14,
        textColor=c_emerald,
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True,
    )

    body_style = ParagraphStyle(
        'Body_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12.5,
        textColor=c_text,
        spaceAfter=6,
    )

    prompt_box_style = ParagraphStyle(
        'PromptBox',
        parent=styles['Code'],
        fontName='Courier',
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor("#0f172a"),
    )

    meta_label = ParagraphStyle('MetaLabel', fontName='Helvetica-Bold', fontSize=8, leading=10.5, textColor=c_primary)
    meta_val = ParagraphStyle('MetaVal', fontName='Helvetica', fontSize=8, leading=10.5, textColor=c_text)

    story = []

    # =========================================================================
    # PAGE 1: TITLE, EXECUTIVE SUMMARY & ARCHITECTURAL DECISIONS
    # =========================================================================
    story.append(Paragraph("India Legal News Aggregator (v2.1)", title_style))
    story.append(Paragraph("Production Implementation & Phase-Wise Engineering Blueprint", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=c_accent, spaceBefore=0, spaceAfter=8))

    meta_data = [
        [Paragraph("Target Version:", meta_label), Paragraph("v2.1 Production Baseline", meta_val),
         Paragraph("Cloud Infrastructure:", meta_label), Paragraph("Render.com + Neon (pgvector) + Vercel", meta_val)],
        [Paragraph("RAM Budget:", meta_label), Paragraph("&lt; 250 MB (Strict $0/mo Free Tier)", meta_val),
         Paragraph("Core Architecture:", meta_label), Paragraph("FastAPI + ONNX Runtime + React 18", meta_val)],
        [Paragraph("Execution Model:", meta_label), Paragraph("4 Isolated Phased Chats", meta_val),
         Paragraph("Key Features:", meta_label), Paragraph("3-State Classifier, VIP API Gate, 1.15x RRF Boost", meta_val)],
    ]
    t_meta = Table(meta_data, colWidths=[105, 140, 115, 125])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), c_bg_light),
        ('BOX', (0, 0), (-1, -1), 0.5, c_border),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 10))

    story.append(Paragraph("1. Executive Summary & Core Engineering Decisions", h1_style))
    story.append(Paragraph(
        "The platform ingests legal data from the Supreme Court of India, Indian Kanoon, LiveLaw, and Bar &amp; Bench. "
        "A critical problem in legal platforms is the confusion between <b>legal journalism</b> (collegium appointments, "
        "advocate interviews, policy news) and <b>binding judicial orders</b> (bail grants, quashing decrees, writ rulings). "
        "Version 2.1 resolves this permanently by introducing an explicit 3-state content taxonomy (<code>judgment</code>, "
        "<code>news</code>, <code>unknown</code>), deploying a two-lane security gateway for partner applications (e.g. LawPro), "
        "and tuning hybrid search with a 1.15x Reciprocal Rank Fusion boost for case law.",
        body_style
    ))

    dec_data = [
        [Paragraph("<b>Pillar</b>", meta_label), Paragraph("<b>Engineering Decision &amp; Mechanism</b>", meta_label), Paragraph("<b>Strategic Impact</b>", meta_label)],
        [
            Paragraph("<b>1. Explicit 3-State Taxonomy</b>", body_style),
            Paragraph("Tag records as <code>judgment</code>, <code>news</code>, or <code>unknown</code> using deterministic source routes and syntactic legal heuristics.", body_style),
            Paragraph("Prevents legal journalism from diluting case law search; gives external apps pure precedent feeds.", body_style)
        ],
        [
            Paragraph("<b>2. Two-Lane API Security</b>", body_style),
            Paragraph("Public web requests are IP-rate limited (30 req/min) and cached. VIP callers (<code>X-API-Key</code>) enjoy zero rate limits and priority execution.", body_style),
            Paragraph("Ensures partner apps (like LawPro) never hit 429 throttles while protecting free-tier Render RAM and Neon connections.", body_style)
        ],
        [
            Paragraph("<b>3. Hybrid RRF 1.15x Boost</b>", body_style),
            Paragraph("In general search, multiply the fused BM25 + pgvector score by 1.15x for records where <code>content_type == 'judgment'</code>.", body_style),
            Paragraph("Binding judicial orders naturally surface to rank #1 and #2, with supporting commentary positioned directly below.", body_style)
        ],
        [
            Paragraph("<b>4. Zero-Downtime DB Backfill</b>", body_style),
            Paragraph("Instant SQL update marks 100% of SCI/Kanoon records as judgments, followed by a batched async classifier for LiveLaw/B&amp;B.", body_style),
            Paragraph("Upgrades existing database in &lt; 10 seconds without locks or container memory spikes.", body_style)
        ]
    ]
    t_dec = Table(dec_data, colWidths=[105, 230, 150])
    t_dec.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
        ('GRID', (0, 0), (-1, -1), 0.5, c_border),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t_dec)

    # =========================================================================
    # PAGE 2: ROADMAP, ARCHITECTURE DIAGRAM & DEPLOYMENT CHECKLIST
    # =========================================================================
    story.append(PageBreak())
    story.append(Paragraph("2. Strategic Product Roadmap (v2.0 – v3.0)", h1_style))

    roadmap_data = [
        [Paragraph("<b>Version</b>", meta_label), Paragraph("<b>Release Theme</b>", meta_label), Paragraph("<b>Core Deliverables</b>", meta_label), Paragraph("<b>Effort</b>", meta_label)],
        [Paragraph("<b>v2.0</b>", body_style), Paragraph("Baseline MVP Stack", body_style), Paragraph("ONNX quantized miniLM, pgvector, hybrid BM25 search, &lt; 250 MB RAM budget.", body_style), Paragraph("Current", meta_val)],
        [Paragraph("<b>v2.1</b>", body_style), Paragraph("Developer API &amp; Classification", body_style), Paragraph("3-state classifier, VIP API Key gate, public abuse shields, 1.15x RRF boost.", body_style), Paragraph("Phase 1-4", meta_val)],
        [Paragraph("<b>v2.2</b>", body_style), Paragraph("Unified Observability", body_style), Paragraph("Single-glance ops dashboard for Render, Neon, Vercel &amp; Ingest worker health.", body_style), Paragraph("2-3 Days", meta_val)],
        [Paragraph("<b>v2.3</b>", body_style), Paragraph("BNS/BNSS Transition &amp; AI", body_style), Paragraph("Statute transition mapper (IPC/CrPC to BNS/BNSS), automated judgment headnotes.", body_style), Paragraph("3-4 Days", meta_val)],
        [Paragraph("<b>v2.4</b>", body_style), Paragraph("Tribunals &amp; Resiliency", body_style), Paragraph("NCLT/NCLAT &amp; ITAT feeds, circuit-breaker ingestion, 90-day text pruning.", body_style), Paragraph("3-4 Days", meta_val)],
        [Paragraph("<b>v3.0</b>", body_style), Paragraph("Legal Developer Hub", body_style), Paragraph("Self-service API keys, real-time webhooks, and visual citation precedent graph.", body_style), Paragraph("Major", meta_val)],
    ]
    t_road = Table(roadmap_data, colWidths=[40, 125, 260, 60])
    t_road.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
        ('GRID', (0, 0), (-1, -1), 0.5, c_border),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(t_road)
    story.append(Spacer(1, 10))

    story.append(Paragraph("3. Technical Architecture & Two-Lane Flow", h1_style))
    arch_code = (
        "                    [ INCOMING CLIENT REQUEST ]\n"
        "                                 │\n"
        "             ┌───────────────────┴───────────────────┐\n"
        "             ▼                                       ▼\n"
        "   [ Anonymous Public ]                    [ VIP Partner / App ]\n"
        "   (Web visitors / bots)                   (LawPro / Developer Tools)\n"
        "             │                                       │\n"
        "     No X-API-Key header                    Header: X-API-Key: &lt;token&gt;\n"
        "             ▼                                       ▼\n"
        "   ┌────────────────────┐                  ┌────────────────────┐\n"
        "   │ Rate Limit: 30/min │                  │  Unthrottled Pass  │\n"
        "   │ 15-min Redis Cache │                  │ Priority Execution │\n"
        "   └─────────┬──────────┘                  └─────────┬──────────┘\n"
        "             │                                       │\n"
        "             └───────────────────┬───────────────────┘\n"
        "                                 ▼\n"
        "               [ Hybrid Search & pgvector RRF Engine ]\n"
        "                 (1.15x Boost on content_type='judgment')"
    )
    t_arch = Table([[Paragraph(f"<pre>{escape(arch_code)}</pre>", prompt_box_style)]], colWidths=[485])
    t_arch.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(t_arch)
    story.append(Spacer(1, 10))

    story.append(Paragraph("4. Production Environment Configuration", h1_style))
    env_data = [
        [Paragraph("<b>Environment Variable</b>", meta_label), Paragraph("<b>Recommended Setting</b>", meta_label), Paragraph("<b>Operational Purpose</b>", meta_label)],
        [Paragraph("<code>AUTHORIZED_API_KEYS</code>", body_style), Paragraph("<code>lawpro_sec_...,admin_sec_...</code>", body_style), Paragraph("Comma-separated VIP tokens for partner apps.", body_style)],
        [Paragraph("<code>PUBLIC_SEARCH_RATE_LIMIT</code>", body_style), Paragraph("<code>30</code>", body_style), Paragraph("Max searches per minute for anonymous public IPs.", body_style)],
        [Paragraph("<code>ENVIRONMENT</code>", body_style), Paragraph("<code>production</code>", body_style), Paragraph("Automatically disables /docs, /redoc, and /openapi.json.", body_style)],
        [Paragraph("<code>CORS_ORIGINS</code>", body_style), Paragraph("<code>https://law-aggregator.vercel.app</code>", body_style), Paragraph("Restricts browser cross-origin requests to your SPA.", body_style)],
    ]
    t_env = Table(env_data, colWidths=[150, 155, 180])
    t_env.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
        ('GRID', (0, 0), (-1, -1), 0.5, c_border),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(t_env)

    # =========================================================================
    # PAGES 3 - 6: PHASE-WISE EXECUTION PROMPTS
    # =========================================================================
    def add_prompt_page(phase_num, title, subtitle, prompt_text):
        story.append(PageBreak())
        story.append(Paragraph(f"{phase_num}. {title}", h1_style))
        story.append(Paragraph(subtitle, subtitle_style))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cbd5e1"), spaceBefore=0, spaceAfter=6))
        story.append(Paragraph("<b>Copy and paste this complete prompt into a new chat to execute this phase:</b>", body_style))

        box_elements = []
        for line in prompt_text.strip().split("\n"):
            if not line.strip():
                box_elements.append(Spacer(1, 3))
            else:
                esc_line = escape(line)
                if esc_line.startswith("#"):
                    box_elements.append(Paragraph(f"<b>{esc_line}</b>", prompt_box_style))
                else:
                    box_elements.append(Paragraph(esc_line, prompt_box_style))

        t_box = Table([[box_elements]], colWidths=[485])
        t_box.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#94a3b8")),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(t_box)

    # Phase 1
    p1_text = """# Task: India Legal News Aggregator — v2.1 Phase 1: Content Classification Engine & DB Migration

You are working in d:\\news aggregator\\New folder.
This is a FastAPI + PostgreSQL (pgvector) + React application operating under a strict < 250 MB RAM budget.

## Objective
Implement an explicit 3-state content classification system ('judgment', 'news', 'unknown') across the database schema, Alembic migrations, heuristic classifier, and RSS ingestion pipeline.

## Requirements

### 1. Database Model (backend/app/models/judgment.py)
- Add two new columns to the Judgment model:
  - content_type: Column(String(20), nullable=False, default="unknown", index=True)
  - content_type_confidence: Column(Float, nullable=False, default=0.0)
- Ensure an index named idx_judgments_content_type is created.

### 2. Alembic Migration & Zero-Downtime Backfill
- Generate and run a new Alembic migration script in backend/alembic/versions/:
  - Adds the columns and index.
  - Runs an immediate SQL backfill:
    UPDATE judgments SET content_type = 'judgment', content_type_confidence = 1.0 WHERE source IN ('sci', 'indiankanoon');
  - For remaining rows from livelaw and barandbench: evaluate against heuristic classifier or default to 'unknown'.

### 3. Heuristic Content Classifier (backend/app/services/legal_classifier.py)
- Implement high-speed classification function:
  classify_content_type(title: str, text: str, source: str, url: str) -> tuple[str, float]
  - Returns ("judgment" | "news" | "unknown", confidence_float).
  - Rule A (Source/Route): source in ('sci', 'indiankanoon') -> ("judgment", 1.0). URLs with /columns/, /news/, /law-firms/ -> "news". URLs with /orders/ -> "judgment".
  - Rule B (Judicial Markers): ' vs ', ' v. ', 'In re:', case numbers, CORAM, BAIL GRANTED, DISPOSED OF -> "judgment".
  - Rule C (Journalistic Markers): 'reported on Monday', 'told reporters', 'press release', 'collegium' -> "news".
  - Rule D (Fallback): Confidence < 0.65 -> "unknown".

### 4. Ingestion Worker (backend/app/workers/ingestion_worker.py)
- Call classify_content_type(...) during RSS ingestion and persist both fields.

### 5. Pydantic Schemas (backend/app/schemas/judgment.py)
- Update JudgmentResponse and JudgmentListItem to expose content_type and content_type_confidence.

### 6. Tests (backend/tests/test_content_classifier.py)
- Test SCI/Kanoon classified as 'judgment'.
- Test LiveLaw/B&B bail and quashing orders classified as 'judgment'.
- Test collegium and appointment articles classified as 'news'.
- Test fallback to 'unknown'.

## Verification & Git Push
Run: .\\.venv\\Scripts\\pytest tests/test_content_classifier.py -v
git add .
git commit -m "feat(v2.1): implement 3-state content classification (news, judgment, unknown)"
git push origin main"""
    add_prompt_page("5", "Phase 1 Execution Prompt", "Content Classification Engine, Database Migration & Backfill", p1_text)

    # Phase 2
    p2_text = """# Task: India Legal News Aggregator — v2.1 Phase 2: Hybrid Search RRF Boost & API Filtering

You are working in d:\\news aggregator\\New folder.
Phase 1 has already added content_type ('judgment', 'news', 'unknown') to the database and schemas.

## Objective
Enable explicit content_type filtering on all public feed and search endpoints, and apply a 1.15x Reciprocal Rank Fusion (RRF) ranking boost to judgment records in hybrid search.

## Requirements

### 1. API Endpoints Update (backend/app/api/v1/judgments.py)
- In GET /api/v1/judgments:
  - Add optional query parameter: content_type: str | None = Query(default=None, regex="^(judgment|news|unknown)$")
  - When provided, filter SQL query: where(Judgment.content_type == content_type).
- In GET /api/v1/search and GET /api/v1/judgments/search:
  - Add optional query parameter: content_type: str | None = Query(default=None, regex="^(judgment|news|unknown)$")
  - Pass content_type into search_service.search(...).

### 2. Search Service & Hybrid RRF Boost (backend/app/services/search_service.py)
- In the Reciprocal Rank Fusion algorithm:
  - If content_type filter is passed: restrict both BM25 (tsvector) and pgvector cosine queries to that content_type.
  - If NO content_type filter is passed (default search):
    - Score results with RRF = 1 / (k + rank).
    - Apply a 1.15x multiplier to the fused score of any result where content_type == 'judgment'.
    - Re-sort combined result list by boosted score so binding judgments bubble up naturally above commentary.

### 3. Tests (backend/tests/test_search_content_type.py)
- Test GET /api/v1/judgments?content_type=judgment returns only judgments.
- Test GET /api/v1/judgments?content_type=news returns only news.
- Test GET /api/v1/search?q=bail&content_type=judgment enforces filter.
- Test default search applies 1.15x RRF boost for judgments over matching news articles.
- Test invalid content_type returns 422 Unprocessable Entity.

## Verification & Git Push
Run: .\\.venv\\Scripts\\pytest tests/test_search_content_type.py -v
git add .
git commit -m "feat(v2.1): add content_type API filters and 1.15x RRF ranking boost for judgments"
git push origin main"""
    add_prompt_page("6", "Phase 2 Execution Prompt", "Hybrid Search RRF 1.15x Boost & API Query Filtering", p2_text)

    # Phase 3
    p3_text = """# Task: India Legal News Aggregator — v2.1 Phase 3: VIP API Key Gatekeeper & Public Abuse Shields

You are working in d:\\news aggregator\\New folder.
This backend is hosted on Render free tier (512 MB RAM limit).

## Objective
Implement a secure VIP API Key system (X-API-Key) so authorized external apps (like LawPro or personal scripts) get unthrottled, priority access, while protecting public search endpoints with IP-based rate limiting, caching, and production Swagger lockdown.

## Requirements

### 1. Configuration (backend/app/core/config.py)
- Add AUTHORIZED_API_KEYS: list[str] loaded from environment variable (comma-separated or JSON list). Default to empty list in dev.
- Add PUBLIC_SEARCH_RATE_LIMIT_PER_MINUTE: int = Field(default=30) for anonymous callers.

### 2. VIP Security Dependency (backend/app/api/deps.py or auth.py)
- Create dependency get_api_client_tier(request: Request) -> str:
  - Reads header X-API-Key.
  - If header is present and in settings.AUTHORIZED_API_KEYS -> return "vip".
  - Otherwise return "public".

### 3. Wire Rate Limiter on Search & Judgments (backend/app/api/v1/judgments.py)
- If client tier is "vip": bypass rate limiting completely.
- If client tier is "public": track requests by client IP. If requests exceed 30/minute, return 429 Too Many Requests.

### 4. Hot Query Caching (backend/app/services/cache_service.py & search_service.py)
- Cache results for common query hashes in Redis (with in-memory LRU fallback) for 15 minutes.
- Cache key: search:{hash(normalized_query + court + content_type)}.
- Cache hits return in < 5ms without running pgvector or ONNX inference.

### 5. Production Hardening (backend/app/main.py)
- If settings.ENVIRONMENT == "production": set docs_url=None, redoc_url=None, openapi_url=None.
- Refuse startup if JWT_SECRET is left as the default dev key in production.

### 6. Tests (backend/tests/test_api_security_and_rate_limit.py)
- Test VIP request with valid X-API-Key bypasses rate limits across 50 rapid calls.
- Test anonymous caller hitting /api/v1/search receives 429 after exceeding limit.
- Test search caching avoids duplicate DB queries.
- Test docs are hidden in production environment.

## Verification & Git Push
Run: .\\.venv\\Scripts\\pytest tests/test_api_security_and_rate_limit.py -v
git add .
git commit -m "feat(v2.1): implement VIP API key gatekeeper, search rate limiting, and caching"
git push origin main"""
    add_prompt_page("7", "Phase 3 Execution Prompt", "VIP API Key Gatekeeper & Public Abuse Rate Limiter", p3_text)

    # Phase 4
    p4_text = """# Task: India Legal News Aggregator — v2.1 Phase 4: Frontend UI Filter Tabs & Card Badges

You are working in d:\\news aggregator\\New folder.
Backend v2.1 now exposes content_type on all endpoints and returns content_type on every judgment.

## Objective
Update the React 18 + Vite + Tailwind frontend to include a 3-way content type filter tab and visual badges distinguishing judgments, news, and unverified orders on all cards.

## Requirements

### 1. API Client (frontend/src/api/ or services/)
- Update judgment fetching and search functions to accept contentType?: 'judgment' | 'news' | 'unknown'.
- Pass it as ?content_type=${contentType} when set.

### 2. Content Type Navigation Pills (Feed & Search Views)
- Add a sticky or header filter bar:
  - [ All Updates ] (Default)
  - [ ⚖️ Judgments & Orders ] (content_type=judgment)
  - [ 📰 Legal News ] (content_type=news)
- Active tab should have an accessible active style (Tailwind: bg-slate-900 text-white dark:bg-emerald-600).
- Switching tabs immediately re-queries the feed or search results.

### 3. Visual Badges on Judgment / Article Cards
- On every card in the feed and search results, display a clear, color-coded badge:
  - 'judgment': Badge ⚖️ COURT ORDER / JUDGMENT (Emerald green: bg-emerald-50 text-emerald-700 border-emerald-200).
  - 'news': Badge 📰 LEGAL NEWS (Sky blue: bg-sky-50 text-sky-700 border-sky-200).
  - 'unknown': Badge ⏳ ORDER UPDATE (Slate/gray: bg-slate-50 text-slate-600 border-slate-200).

### 4. Tests & Build Verification
- Add Vitest / React Testing Library tests verifying:
  - Filter pills trigger the correct API query parameter.
  - Cards render the correct badges based on content_type.
- Run frontend build to guarantee TypeScript types and bundle succeed without errors.

## Verification & Git Push
Run inside frontend/:
npm test
npm run build
git add .
git commit -m "feat(v2.1): add frontend content_type filter tabs and card badges"
git push origin main"""
    add_prompt_page("8", "Phase 4 Execution Prompt", "Frontend UI Filter Navigation & Color-Coded Card Badges", p4_text)

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully created: {output_path}")


if __name__ == "__main__":
    out_dir = os.path.join(os.getcwd(), "docs")
    os.makedirs(out_dir, exist_ok=True)
    out_pdf = os.path.join(out_dir, "India_Legal_News_Aggregator_v2.1_Execution_Plan.pdf")
    create_execution_plan_pdf(out_pdf)
