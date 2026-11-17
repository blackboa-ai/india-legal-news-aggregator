# 📡 India Legal Aggregator — Verified Endpoint Details for LawPro

**Exact Verified Target URL:**  
```text
https://india-legal-news-api.onrender.com/api/v1/judgments?limit=1
```

**Status:** **`HTTP 200 OK` (Verified Live)**  
**Content-Type:** `application/json`  
**Authentication Required:** None (Public Endpoint)  

---

## 1. Domain Clarification

* **The Live Production Host is:** `https://india-legal-news-api.onrender.com` *(contains `news`)*.
* *(Note: The alternate subdomain `india-legal-aggregator-api` returns Render 404 Not Found because the service was named `india-legal-news-api` in the Render Cloud Console).*

---

## 2. Actual Live Output from Successful Request

```http
HTTP/1.1 200 OK
Date: Tue, 17 Nov 2026 02:18:41 GMT
Content-Type: application/json
Cache-Control: public, max-age=30, stale-while-revalidate=60
x-render-origin-server: uvicorn
x-response-time-ms: 994.24
```

```json
{
  "total": 33,
  "limit": 1,
  "offset": 0,
  "data": [
    {
      "id": "39ef453e-8473-48c5-a1a9-1dae56fc7f02",
      "external_id": "918ac698d199a6e1f452d7f54bec8625c55c0d132f867aa1ecd52d281de83155",
      "title": "Private life, public disclosure: Nvidia’s CEO crisis in Indian securities law",
      "short_title": "Private life, public disclosure: Nvidia’s CEO crisis in Indian securities law",
      "court_code": "sc",
      "court_name": "Supreme Court of India",
      "court_level": 1,
      "judgment_date": "2026-11-16",
      "subject_category": "Civil",
      "content_type": "news",
      "content_type_confidence": 0.8,
      "excerpt": "On November 12, 2026, Nvidia Corporation",
      "summary": "On November 12, 2026, Nvidia Corporation",
      "full_text": null,
      "source": "barandbench",
      "url": "https://www.barandbench.com/columns/private-life-public-disclosure-nvidias-ceo-crisis-in-indian-securities-law",
      "parties": [],
      "tags": [],
      "is_archived": true,
      "classification_confidence": 0.35,
      "created_at": "2026-11-16T15:58:24.863683Z",
      "updated_at": "2026-11-16T17:37:32.374052Z"
    }
  ],
  "items": [
    {
      "id": "39ef453e-8473-48c5-a1a9-1dae56fc7f02",
      "title": "Private life, public disclosure: Nvidia’s CEO crisis in Indian securities law",
      "court_name": "Supreme Court of India",
      "court_level": 1,
      "judgment_date": "2026-11-16",
      "subject_category": "Civil",
      "content_type": "news",
      "content_type_confidence": 0.8
    }
  ]
}
```

---

## 3. LawPro Terminal Verification Command

```bash
curl -i -X GET "https://india-legal-news-api.onrender.com/api/v1/judgments?limit=1"
```
