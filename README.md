# India Legal News Aggregator (v2.0)

[![CI/CD Pipeline](https://github.com/mahad/india-legal-aggregator/actions/workflows/ci.yml/badge.svg)](https://github.com/mahad/india-legal-aggregator/actions/workflows/ci.yml)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111.0-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15%20%2B%20pgvector-336791?style=flat&logo=postgresql&logoColor=white)](https://github.com/pgvector/pgvector)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=flat&logo=react&logoColor=black)](https://react.dev)
[![Vite](https://img.shields.io/badge/Vite-5-646CFF?style=flat&logo=vite&logoColor=white)](https://vitejs.dev)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-3.4-38B2AC?style=flat&logo=tailwind-css&logoColor=white)](https://tailwindcss.com)
[![Hosting Cost](https://img.shields.io/badge/Cloud%20Cost-%240.00%2Fmonth-brightgreen)](https://render.com)

A high-performance, memory-optimized legal intelligence platform and news aggregator tracking judgments from the **Supreme Court of India**, **High Courts (Delhi, Bombay, Madras, etc.)**, and leading legal publications (**Indian Kanoon**, **LiveLaw**, **Bar & Bench**).

Engineered to operate strictly within a **< 250 MB RAM budget** on **$0/month permanent free-tier cloud infrastructure** (Render.com + Neon/Supabase PostgreSQL + Upstash Redis + Vercel).

---

## 1. Architecture & v2.0 Engineering Upgrades

```
                                  +-------------------------------------------------+
                                  |                 Vercel Frontend                 |
                                  |    (React 18 + Vite + TypeScript + Tailwind)    |
                                  +-----------------------+-------------------------+
                                                          |
                                      HTTPS JSON + Bearer | JWT (?token= SSO Handoff)
                                                          v
                                  +-------------------------------------------------+
                                  |             Render.com Web Service              |
                                  |       FastAPI Backend (< 250 MB RAM Budget)     |
                                  |  - Production Security Headers Middleware       |
                                  |  - Structured Latency Logging (X-Response-Time) |
                                  |  - Global Exception Envelopes (No Stack Leaks)  |
                                  +-----------+-------------------------+-----------+
                                              |                         |
                         Read / Write Queries |                         | Cache (300s) & Rate Limits
                                              v                         v
                       +-------------------------------+   +------------------------+
                       |    Neon / Supabase Postgres   |   |     Upstash Redis      |
                       | - PostgreSQL 15 + pgvector    |   | - Serverless Redis     |
                       | - Reciprocal Rank Fusion      |   | - In-memory fallback   |
                       | - HNSW (Cosine) + GIN (BM25)  |   | - 100 req/min limits   |
                       +-------------------------------+   +------------------------+
                                              ^
                                              | Background Polling (Every 20 mins)
                                              |
                                  +-----------+-------------------------+
                                  |         APScheduler Ingestor        |
                                  | - Indian Kanoon, SCI, LiveLaw, B&B  |
                                  | - SHA-256 Duplicate Suppression     |
                                  | - 10 Indian Law Classifier (Rules)  |
                                  | - 384-dim ONNX / HF MiniLM Embedder |
                                  +-------------------------------------+
```

### Five Core v2.0 Architectural Upgrades

| Upgrade Area | v1.0 Bottleneck | v2.0 Production Solution |
| :--- | :--- | :--- |
| **1. Memory Footprint** | PyTorch + sentence-transformers used 1.5–2.5 GB RAM, crashing 512 MB free containers. | **ONNX-quantized `all-MiniLM-L6-v2`** via `onnxruntime` (~85 MB RAM) or Hugging Face Inference API. Container runs < 250 MB RAM. |
| **2. Unified Vector DB** | Architecture split data between ChromaDB and PostgreSQL. | Standardized on **PostgreSQL 15 + pgvector**; relational metadata, GIN full-text index, and 384-dim HNSW embeddings live in a single ACID database. |
| **3. Hybrid Legal Search** | Pure vector search missed exact Indian statutes (e.g. *Sec 438 CrPC*, *Sec 482 BNSS*, *Art 21*). | **Reciprocal Rank Fusion (RRF, $k=60$)** combining PostgreSQL `tsvector` keyword ranking with pgvector cosine similarity. |
| **4. Async RSS Ingestion** | Synchronous feed polling blocked incoming API requests. | **APScheduler async background worker** running every 20 minutes with SHA-256 external URL/citation deduplication and error isolation per feed. |
| **5. Permanent $0 Cloud Stack** | Render free PostgreSQL expires after 30 days. | **Neon / Supabase** (free serverless PostgreSQL with pgvector), **Upstash** (free serverless Redis), **Render** (FastAPI backend), and **Vercel** (Vite SPA). |

---

## 2. Canonical Repository Layout

```
india-legal-aggregator/
├── .github/
│   └── workflows/
│       └── ci.yml                 # Automated ruff, pytest, vitest, and build CI
├── docs/
│   └── India_Legal_News_Aggregator_Master_Execution_Plan_v2.pdf
├── render.yaml                    # Render.com Infrastructure Blueprint ($0 tier)
├── backend/
│   ├── Dockerfile                 # Multi-stage Python 3.11-slim (< 250 MB RAM)
│   ├── requirements.txt           # Production dependencies (no PyTorch)
│   ├── alembic/                   # Database migrations + pgvector setup
│   ├── alembic.ini
│   ├── app/
│   │   ├── main.py                # FastAPI app, security headers, latency logging
│   │   ├── core/
│   │   │   ├── config.py          # Pydantic BaseSettings (.env validation)
│   │   │   └── database.py        # Async SQLAlchemy 2.0 engine + session pool
│   │   ├── models/                # Judgment, Bookmark, Alert, Topic, TopicJudgment
│   │   ├── schemas/               # Pydantic v2 DTOs
│   │   ├── auth/                  # JWT tokens + Google OAuth + rate limiting
│   │   ├── api/v1/
│   │   │   ├── health.py          # GET /api/v1/health
│   │   │   ├── judgments.py       # GET /judgments, /search, /similar/{id}
│   │   │   ├── auth.py            # POST /auth/register, /login, /google, /me
│   │   │   ├── bookmarks.py       # POST/GET/DELETE /bookmarks, /alerts
│   │   │   ├── user.py            # POST/GET/DELETE /topics, /topics/{id}/judgments
│   │   │   └── admin.py           # POST /admin/refresh (manual RSS ingestion)
│   │   ├── services/
│   │   │   ├── rss_ingestor.py    # Async feedparser + BeautifulSoup scraper
│   │   │   ├── legal_classifier.py# 10 Indian law category + statute extractor
│   │   │   ├── embedder.py        # Lightweight 384-dim ONNX text embedder
│   │   │   ├── search_service.py  # Hybrid RRF search engine
│   │   │   ├── cache_service.py   # Upstash Redis caching & rate limiting
│   │   │   └── scheduler.py       # APScheduler 20-min background ingestion loop
│   │   └── workers/
│   │       └── ingestion_worker.py# Feed polling & database upsert worker
│   └── tests/                     # 174+ comprehensive unit & integration tests
└── frontend/
    ├── package.json               # React 18, TypeScript, Tailwind CSS, Lucide
    ├── vercel.json                # Vercel SPA rewrites & security headers
    ├── vite.config.ts
    ├── tailwind.config.js
    └── src/
        ├── api/client.ts          # Typed fetch client (Standalone + SSO handoff)
        ├── components/            # SearchAndFilters, JudgmentCard, Modals, Drawer
        ├── types/                 # TypeScript interfaces
        └── App.tsx                # Main legal research dashboard
```

---

## 3. Database Schema & Hybrid Search Contract

### PostgreSQL + pgvector Schema

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE judgments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id VARCHAR(128) UNIQUE NOT NULL, -- SHA-256 hash of URL/citation
    title TEXT NOT NULL,
    short_title VARCHAR(500),
    court_code VARCHAR(50) NOT NULL,          -- 'sc', 'delhi-hc', 'bombay-hc', etc.
    court_name VARCHAR(120) NOT NULL,
    court_level INTEGER NOT NULL DEFAULT 2,   -- 1: Supreme Court, 2: High Court, 3: Tribunal
    judgment_date DATE NOT NULL,
    subject_category VARCHAR(50) NOT NULL,    -- 10 standardized categories
    excerpt TEXT NOT NULL,
    full_text TEXT,
    url TEXT NOT NULL,
    parties JSONB DEFAULT '[]'::jsonb,
    tags TEXT[] DEFAULT '{}',                 -- e.g. ['IPC', 'Section 438 CrPC', 'Article 21']
    source VARCHAR(50) NOT NULL,              -- 'indiankanoon', 'livelaw', 'barandbench', 'sci'
    is_archived BOOLEAN DEFAULT TRUE,
    classification_confidence FLOAT DEFAULT 0.0,
    embedding VECTOR(384),                    -- Quantized MiniLM embedding
    search_tsv TSVECTOR GENERATED ALWAYS AS (
        to_tsvector('english', coalesce(title, '') || ' ' || coalesce(excerpt, ''))
    ) STORED,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Fast GIN and HNSW Indexes
CREATE INDEX idx_judgments_tsv ON judgments USING GIN(search_tsv);
CREATE INDEX idx_judgments_embedding ON judgments USING HNSW (embedding vector_cosine_ops);
CREATE INDEX idx_judgments_category ON judgments(subject_category);
CREATE INDEX idx_judgments_court ON judgments(court_code);
CREATE INDEX idx_judgments_date ON judgments(judgment_date DESC);
```

### Standardized Indian Legal Subject Categories (10)
1. **Constitutional Law** (Fundamental Rights, Writ Petitions, Basic Structure, Art 14/19/21/32)
2. **Criminal Law** (IPC, BNS, CrPC, BNSS, Bail, NDPS, Prevention of Corruption)
3. **Civil Law** (CPC, Specific Relief, Injunctions, Property, Succession)
4. **Corporate & Commercial Law** (Companies Act, IBC, Insolvency, Arbitration, Contract Act)
5. **Administrative Law** (Service matters, Government tenders, Disciplinary proceedings)
6. **Human Rights & Civil Liberties** (Custodial deaths, Police atrocities, Habeas Corpus)
7. **Environmental Law** (NGT, Forest Conservation, Environmental Protection Act)
8. **Labour & Employment Law** (Industrial Disputes, Gratuity, EPF, Trade Unions)
9. **Family Law** (Hindu Marriage Act, Special Marriage Act, Guardianship, Domestic Violence)
10. **Education & Service Law** (UGC, University admissions, Quota, Recruitment reservations)

### REST API Endpoints

| Method | Endpoint | Access | Purpose |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` & `/api/v1/health` | Public | Service health probe (Render / uptime monitors) |
| `GET` | `/api/v1/judgments` | Public | List filtered judgments (cached in Redis 300s) |
| `GET` | `/api/v1/search` | Public | Hybrid RRF / Keyword / Semantic legal search |
| `GET` | `/api/v1/judgments/{id}` | Public | Detailed judgment record with full text & parties |
| `GET` | `/api/v1/similar/{id}` | Public | Top 5 similar precedents via pgvector cosine distance |
| `GET` | `/api/v1/categories` & `/courts` | Public | Legal categories and Indian court metadata |
| `POST` | `/api/v1/auth/register` | Public | Email + password user registration |
| `POST` | `/api/v1/auth/login` | Public | Standard JWT token authentication |
| `POST` | `/api/v1/auth/google` | Public | Google OAuth SSO token verification |
| `GET` | `/api/v1/auth/me` | JWT | Current authenticated user profile |
| `POST` / `GET` / `DELETE` | `/api/v1/bookmarks` | JWT | Save, list, or remove bookmarked judgments |
| `POST` / `GET` / `DELETE` | `/api/v1/alerts` | JWT | Topic/keyword alerts & matched judgment queries |
| `POST` / `GET` / `DELETE` | `/api/v1/topics` | JWT | Research folders & precedent organizing |
| `POST` | `/api/v1/admin/refresh` | Admin Key | Trigger immediate asynchronous RSS ingestion cycle |

---

## 4. Local Quick-Start Guide

### Prerequisites
- **Python 3.11+**
- **Node.js 20+** & **npm**
- **PostgreSQL 15+** with the `pgvector` extension (or a free Neon cloud database)
- Optional: **Redis** (or uses in-memory cache automatically)

### Step 1: Clone Repository
```bash
git clone https://github.com/mahad/india-legal-aggregator.git
cd india-legal-aggregator
```

### Step 2: Configure & Run Backend
```bash
# Navigate to backend
cd backend

# Create and activate Python virtual environment
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows PowerShell:
.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Run database migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
The API is available at:
- **Interactive OpenAPI Documentation:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check Endpoint:** [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

### Step 3: Configure & Run Frontend
```bash
# In a separate terminal, navigate to frontend
cd frontend

# Install Node dependencies
npm install

# Copy environment template
cp .env.example .env

# Start Vite dev server
npm run dev
```
The legal dashboard will launch at: [http://localhost:5173](http://localhost:5173).

---

## 5. Step-by-Step $0/Month Free-Tier Deployment Guide

Follow this 10-step blueprint to host the entire stack permanently without paying a cent.

### Step 1: Provision Free PostgreSQL with pgvector on Neon.tech
1. Sign up for a free account at [Neon.tech](https://neon.tech).
2. Create a new project named `india-legal-aggregator` (select AWS Region `us-east-2` or `eu-central-1`).
3. Neon includes `pgvector` pre-installed on PostgreSQL 15/16.
4. Copy your connection string from the Neon dashboard (e.g. `postgresql://user:password@ep-xyz.us-east-2.aws.neon.tech/neondb?sslmode=require`).

### Step 2: Enable Vector & Pgcrypto Extensions
In the Neon SQL Editor, execute:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
```

### Step 3: Apply Database Migrations
From your local terminal with `DATABASE_URL` pointing to your Neon connection:
```bash
cd backend
DATABASE_URL="postgresql+asyncpg://user:password@ep-xyz.us-east-2.aws.neon.tech/neondb?ssl=require" alembic upgrade head
```

### Step 4: Provision Serverless Redis on Upstash.com
1. Register for a free tier account at [Upstash.com](https://upstash.com).
2. Click **Create Database** -> Choose Redis (Serverless).
3. Set primary region closest to your Render server (e.g. `us-east-1`).
4. Copy the `rediss://...` connection URL from the database details page.

### Step 5: Configure Backend Secrets
Prepare your production environment variables:
- `DATABASE_URL`: `postgresql+asyncpg://...` (from Step 1, with `ssl=require`)
- `REDIS_URL`: `rediss://...` (from Step 4)
- `JWT_SECRET`: Generate a 64-char string: `openssl rand -hex 32`
- `ADMIN_API_KEY`: Generate a random key for manual trigger access
- `EMBEDDING_PROVIDER`: `onnx` (default) or `hf`
- `CORS_ORIGINS`: `["https://your-app.vercel.app","http://localhost:5173"]`

### Step 6: Deploy Backend on Render.com
1. Go to [Render.com](https://render.com) and create a free account.
2. Click **New +** -> **Blueprint**.
3. Connect your GitHub repository `india-legal-aggregator`.
4. Render detects the root `render.yaml` automatically and configures:
   - **Service Name:** `india-legal-aggregator-api`
   - **Environment:** Docker
   - **Plan:** Free (512 MB RAM limit)
   - **Health Check Path:** `/api/v1/health`
   - **Uvicorn Workers:** `1` (ensures container RAM stays under 250 MB)
5. Under Environment Variables, input your `DATABASE_URL` and `REDIS_URL`.
6. Click **Apply Blueprint** and wait for the build to finish.

### Step 7: Verify Backend Health Probe
Once deployed, verify the live health check responds with HTTP 200:
```bash
curl -i https://india-legal-aggregator-api.onrender.com/api/v1/health
```
Expected response:
```json
{"status":"ok","service":"india-legal-aggregator"}
```

### Step 8: Configure Frontend Environment
In `frontend/`:
```bash
VITE_API_BASE_URL=https://india-legal-aggregator-api.onrender.com/api/v1
VITE_GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
```

### Step 9: Deploy Frontend on Vercel
1. Log in to [Vercel.com](https://vercel.com) and click **Add New** -> **Project**.
2. Select your repository.
3. Configure the project settings:
   - **Framework Preset:** Vite
   - **Root Directory:** `frontend`
   - **Build Command:** `npm run build`
   - **Output Directory:** `dist`
4. Add environment variable:
   - `VITE_API_BASE_URL` = `https://india-legal-aggregator-api.onrender.com/api/v1`
5. Click **Deploy**. Vercel will apply the SPA rewrite rules and security headers defined in `frontend/vercel.json`.

### Step 10: Run End-to-End Verification & Initial Ingestion
Trigger the initial legal content ingestion cycle using your Admin Key:
```bash
curl -X POST https://india-legal-aggregator-api.onrender.com/api/v1/admin/refresh \
  -H "X-Admin-Key: your-admin-api-key"
```
Open your Vercel URL in your browser to test hybrid search, statute filtering, bookmarking, and judgment reading.

---

## 6. Production Security & Performance Hardening

- **Strict RAM Containment (< 250 MB):**
  Uses `onnxruntime` quantized MiniLM inference (~85 MB) instead of PyTorch (1.5 GB), running uvicorn with a single worker.
- **Production Security Headers:**
  Every response from FastAPI and Vercel includes:
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `X-XSS-Protection: 1; mode=block`
  - `Referrer-Policy: strict-origin-when-cross-origin`
  - `Strict-Transport-Security: max-age=31536000; includeSubDomains`
  - `Permissions-Policy: accelerometer=(), camera=(), geolocation=(), ...`
  - `Content-Security-Policy: default-src 'self'; frame-ancestors 'none';`
- **Structured Latency Logging & Diagnostics:**
  The `request_latency_and_security_headers_middleware` logs structured metrics (`method`, `path`, `status_code`, `latency_ms`, `client_ip`) and exposes `X-Response-Time-Ms` on every response.
- **Global Error Envelopes:**
  Unhandled exceptions (500), validation errors (422), and HTTP errors (404/401/403) return sanitized JSON error envelopes without exposing internal stack traces, paths, or database errors.

---

## 7. Verification & Automated Test Suite

Both backend and frontend feature automated test suites matching **Exit Gate 5**:

```bash
# Run backend ruff linter
ruff check .

# Run backend pytest suite (174 tests)
pytest backend/tests -v

# Run frontend Vitest suite (19 tests)
npm --prefix frontend test

# Build frontend production bundle
npm --prefix frontend run build
```

---

## 8. License & Legal Feed Attribution

Distributed under the MIT License.

Legal judgment metadata and excerpts are aggregated under Fair Dealing / Public Legal Information access from:
- [Supreme Court of India](https://main.sci.gov.in/)
- [Indian Kanoon](https://indiankanoon.org/)
- [LiveLaw](https://www.livelaw.in/)
- [Bar & Bench](https://www.barandbench.com/)
