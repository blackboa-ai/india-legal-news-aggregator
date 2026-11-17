# ⚖️ India Legal News Aggregator — LawPro Integration Specification (v2.1)

**Target System:** LawPro Litigation Diary & Case Management Suite (`lawpro-five.vercel.app`)  
**Provider:** India Legal News Aggregator API (`india-legal-news-api.onrender.com`)  
**Specification Version:** `2.1.0-production`  
**Protocol:** HTTPS / REST / JSON  
**Authentication Model:** Pre-shared VIP API Key Header (`X-API-Key`)  
**Last Updated:** November 2026  

---

## 1. Executive Summary & Architecture

The **India Legal News Aggregator API** provides Indian legal updates, high-court & supreme-court rulings, statutory citations, and structured legal news to companion legal tech platforms.

For partner applications like **LawPro**, the API operates on a **Two-Lane Highway**:
* **Public Lane:** Anonymous callers are subject to IP-based sliding-window rate limiting (30 req/min).
* **VIP Priority Lane (LawPro):** By supplying the pre-shared `X-API-Key` header, LawPro traffic completely bypasses rate limiting, receives priority route execution, and queries an indexed, RRF-boosted PostgreSQL database.

---

## 2. Environment & Endpoints

### 2.1 Base URLs

| Environment | Base URL |
| :--- | :--- |
| **Production** | `https://india-legal-news-api.onrender.com/api/v1` |
| **Local Staging** | `http://127.0.0.1:8000/api/v1` |

### 2.2 Endpoint Index

| Method | Endpoint | Description | Primary Use in LawPro |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | Service & DB connectivity check | Health probes & cold-start ping |
| `GET` | `/search` | Hybrid keyword + vector precedent search | Researching case laws & authorities |
| `GET` | `/judgments` | Paginated live court orders & legal news feed | Dashboard legal updates widget |
| `GET` | `/judgments/{id}` | Full case details, citations & text | Detailed precedent inspection |

---

## 3. Authentication & VIP Header

All requests initiated by LawPro backend services or server actions should include the `X-API-Key` HTTP header:

```http
X-API-Key: lawpro_live_vip_2026_9f8b4e
```

> **Security Note:**  
> Keep this key inside LawPro's server-side environment variables (`LEGAL_AGGREGATOR_API_KEY`). Do not expose the raw key in client-side public bundles. If calling from browser components, proxy via LawPro Next.js route handlers (`/api/precedents/search`).

---

## 4. Detailed API Specifications

### 4.1 Search Precedents (`GET /search`)

Performs high-performance Reciprocal Rank Fusion (RRF) search across Indian judgments. Binding court orders automatically receive a **1.15x ranking multiplier** over commentary.

#### Query Parameters:

| Parameter | Type | Required | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `q` | `string` | **Yes** | — | Search query (e.g. `Section 438 anticipatory bail`) |
| `mode` | `string` | No | `hybrid` | Search algorithm: `hybrid`, `keyword`, or `semantic` |
| `content_type` | `string` | No | — | Filter by type: `judgment` (court orders) or `news` |
| `category` | `string` | No | — | Legal category: `Criminal`, `Civil`, `Constitutional`, `Corporate`, `Tax`, etc. |
| `court` | `string` | No | — | Court code filter (e.g. `sc`, `delhi-hc`, `madras-hc`, `bombay-hc`) |
| `limit` | `integer`| No | `10` | Number of results to return (max 50) |
| `offset` | `integer`| No | `0` | Pagination offset |

#### Response Schema (`200 OK`):

```json
{
  "query": "anticipatory bail murder",
  "query_type": "hybrid",
  "total": 42,
  "limit": 10,
  "offset": 0,
  "matched_terms": ["anticipatory", "bail", "murder"],
  "results": [
    {
      "id": "e4b2d3c1-7a8f-4c92-b821-2a6d8f1e5c30",
      "title": "State of Maharashtra v. ABC",
      "court_name": "Supreme Court of India",
      "court_level": 1,
      "judgment_date": "2026-11-14",
      "subject_category": "Criminal",
      "content_type": "judgment",
      "content_type_confidence": 0.98,
      "score": 0.0324,
      "excerpt": "Parameters for granting pre-arrest bail in grave criminal allegations...",
      "tags": ["Section 438 CrPC", "Section 302 IPC", "Anticipatory Bail"],
      "source": "sci",
      "url": "https://sci.gov.in/..."
    }
  ]
}
```

---

### 4.2 Paginated Feed (`GET /judgments`)

Retrieves latest indexed rulings and legal news chronologically.

#### Query Parameters:

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `content_type` | `string` | — | `judgment` (orders only) or `news` (commentary) |
| `category` | `string` | — | Subject category filter |
| `court` | `string` | — | Originating judicial court |
| `date_from` | `string` | — | ISO date `YYYY-MM-DD` |
| `date_to` | `string` | — | ISO date `YYYY-MM-DD` |
| `limit` | `integer`| `20` | Page size (1 to 100) |
| `offset` | `integer`| `0` | Offset for pagination |

#### Response Schema (`200 OK`):

```json
{
  "total": 1420,
  "page": 1,
  "page_size": 20,
  "data": [
    {
      "id": "f87a87e2-411a-4ab0-bbfb-3719bca40001",
      "title": "West Bengal moves Supreme Court against Calcutta HC order",
      "court_name": "Supreme Court of India",
      "court_level": 1,
      "judgment_date": "2026-11-16",
      "subject_category": "Constitutional",
      "content_type": "news",
      "content_type_confidence": 0.88,
      "excerpt": "The West Bengal government has moved the Supreme Court challenging...",
      "tags": ["Article 136", "Elections"],
      "source": "barandbench",
      "url": "https://barandbench.com/..."
    }
  ]
}
```

---

### 4.3 Get Judgment Details (`GET /judgments/{id}`)

Fetches complete metadata, full text, citations, and opposing parties for case preparation.

#### Path Parameter:
* `id` (UUID string, e.g. `f87a87e2-411a-4ab0-bbfb-3719bca40001`)

#### Response Schema (`200 OK`):

```json
{
  "id": "f87a87e2-411a-4ab0-bbfb-3719bca40001",
  "title": "Gurbaksh Singh Sibbia v. State of Punjab",
  "short_title": "Gurbaksh Singh Sibbia",
  "court_name": "Supreme Court of India",
  "court_level": 1,
  "court_code": "sc",
  "judgment_date": "2024-04-15",
  "subject_category": "Criminal",
  "content_type": "judgment",
  "content_type_confidence": 1.0,
  "excerpt": "Constitution bench landmark ruling on Section 438 of the Code of Criminal Procedure.",
  "full_text": "...",
  "parties": [
    { "role": "appellant", "name": "Gurbaksh Singh Sibbia" },
    { "role": "respondent", "name": "State of Punjab" }
  ],
  "tags": ["Section 438 CrPC", "Article 21", "Anticipatory Bail"],
  "source": "indiankanoon",
  "url": "https://indiankanoon.org/doc/12345/"
}
```

---

## 5. Drop-in LawPro Integration Code

### 5.1 TypeScript Client for LawPro (`src/lib/aggregatorClient.ts`)

```typescript
/**
 * LawPro Legal Aggregator Integration Client
 * Provides VIP-authenticated access to search precedents and court orders.
 */

const AGGREGATOR_BASE = 
  process.env.LEGAL_AGGREGATOR_URL || 'https://india-legal-news-api.onrender.com/api/v1';

const AGGREGATOR_KEY = 
  process.env.LEGAL_AGGREGATOR_API_KEY || 'lawpro_live_vip_2026_9f8b4e';

export interface PrecedentSearchResult {
  id: string;
  title: string;
  court_name: string;
  court_level: number;
  judgment_date: string;
  subject_category: string;
  content_type: 'judgment' | 'news' | 'unknown';
  excerpt: string;
  tags: string[];
  url: string;
  score?: number;
}

export interface SearchOptions {
  q: string;
  mode?: 'hybrid' | 'keyword' | 'semantic';
  contentType?: 'judgment' | 'news';
  category?: string;
  limit?: number;
  offset?: number;
}

/**
 * Executes a resilient search with automatic cold-start retry
 */
export async function searchAggregatorPrecedents(
  options: SearchOptions,
  attempt = 1
): Promise<{ total: number; results: PrecedentSearchResult[] }> {
  const params = new URLSearchParams({
    q: options.q,
    mode: options.mode || 'hybrid',
    limit: String(options.limit || 10),
    offset: String(options.offset || 0),
  });

  if (options.contentType) {
    params.set('content_type', options.contentType);
  }
  if (options.category) {
    params.set('category', options.category);
  }

  try {
    const res = await fetch(`${AGGREGATOR_BASE}/search?${params.toString()}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': AGGREGATOR_KEY,
      },
      next: { revalidate: 300 }, // Cache on Next.js edge for 5 minutes
    });

    if (!res.ok) {
      // Free-tier cold start handling: auto-retry once after 4 seconds
      if (res.status >= 500 && attempt === 1) {
        await new Promise((r) => setTimeout(r, 4000));
        return searchAggregatorPrecedents(options, attempt + 1);
      }
      throw new Error(`Aggregator API error (${res.status}): ${await res.text()}`);
    }

    return await res.json();
  } catch (err) {
    if (attempt === 1) {
      await new Promise((r) => setTimeout(r, 4000));
      return searchAggregatorPrecedents(options, attempt + 1);
    }
    throw err;
  }
}
```

---

## 6. Cold Start & Infrastructure Best Practices

1. **Render Free Tier Spin-Down:**
   * The free web service spins down after 15 minutes of inactivity. The initial wake-up takes ~30–45 seconds.
   * **Recommendation for LawPro:** Use the built-in cold-start retry logic shown in Section 5.1. Alternatively, LawPro can send a background `GET /health` ping every 10 minutes to keep the instance warm during peak business hours.
2. **Precedents vs. News Filtering:**
   * When attaching authorities to LawPro case files, always query with `content_type=judgment`.
   * For the dashboard updates feed, omit `content_type` or allow users to toggle between `judgment` and `news`.
3. **Data Caching:**
   * Search queries are deterministic and cached for 15 minutes in Redis/memory.
   * Full judgment texts are immutable; LawPro can safely cache individual judgment IDs indefinitely.
