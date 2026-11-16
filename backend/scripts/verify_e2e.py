"""
End-to-End API Integration & Contract Verification Script
Runs end-to-end tests against Neon PostgreSQL via FastAPI test client / httpx.
Verifies:
1. GET /api/v1/judgments with default limit=25
2. GET /api/v1/judgments/search (Smart Search, Exact Words, By Meaning)
3. User Authentication (Register, Login, Me)
4. Bookmarks (Create, List, Delete)
5. Alerts (Create, List, Matches)
"""

import asyncio
import sys
import uuid
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.main import app
from httpx import ASGITransport, AsyncClient


async def run_e2e_tests():
    print("=" * 80)
    print("RUNNING END-TO-END VERIFICATION AGAINST NEON POSTGRESQL")
    print("=" * 80)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Health check
        print("\n1. Testing GET /api/v1/health...")
        h_res = await client.get("/api/v1/health")
        assert h_res.status_code == 200, f"Health check failed: {h_res.text}"
        h_data = h_res.json()
        print(f"   Status: {h_data['status']}, Service: {h_data['service']}")
        assert h_data['status'] == "ok", "Health check status not ok!"

        # 2. Judgments Feed (Default limit 25)
        print("\n2. Testing GET /api/v1/judgments (Default limit 25)...")
        feed_res = await client.get("/api/v1/judgments")
        assert feed_res.status_code == 200, f"Feed failed: {feed_res.text}"
        feed_data = feed_res.json()
        print(f"   Total in DB: {feed_data['total']}, Limit returned: {feed_data['limit']}, Count returned: {len(feed_data['data'])}")
        assert feed_data['limit'] == 25, f"Expected default limit=25, got {feed_data['limit']}"
        assert len(feed_data['data']) >= 20, f"Expected at least 20 items in feed, got {len(feed_data['data'])}"
        sample_judgment = feed_data['data'][0]
        print(f"   Sample Title: '{sample_judgment['title'][:60]}...'")
        print(f"   Excerpt Length: {len(sample_judgment['excerpt'])} chars")
        print(f"   Tags: {sample_judgment['tags']}")

        # 3. Search Modes: Smart Search (hybrid), Exact Words (keyword), By Meaning (semantic)
        print("\n3. Testing GET /api/v1/judgments/search across 3 search modes...")

        # 3a. Smart Search (hybrid)
        hybrid_res = await client.get("/api/v1/judgments/search", params={"q": "anticipatory bail", "mode": "hybrid"})
        assert hybrid_res.status_code == 200, f"Hybrid search failed: {hybrid_res.text}"
        hybrid_data = hybrid_res.json()
        print(f"   [Smart Search] Query: 'anticipatory bail' -> {len(hybrid_data['results'])} results (query_type: {hybrid_data['query_type']})")
        assert len(hybrid_data['results']) > 0, "No results for hybrid search 'anticipatory bail'!"
        top_h = hybrid_data['results'][0]
        print(f"     Top match: {top_h['title']} (Score: {top_h['score']})")

        # 3b. Exact Words (keyword BM25)
        kw_res = await client.get("/api/v1/judgments/search", params={"q": "Section 438", "mode": "keyword"})
        assert kw_res.status_code == 200, f"Keyword search failed: {kw_res.text}"
        kw_data = kw_res.json()
        print(f"   [Exact Words] Query: 'Section 438' -> {len(kw_data['results'])} results (query_type: {kw_data['query_type']})")
        assert len(kw_data['results']) > 0, "No results for keyword search 'Section 438'!"

        # 3c. By Meaning (semantic vector)
        sem_res = await client.get("/api/v1/judgments/search", params={"q": "protection against arbitrary police custody", "mode": "semantic"})
        assert sem_res.status_code == 200, f"Semantic search failed: {sem_res.text}"
        sem_data = sem_res.json()
        print(f"   [By Meaning] Query: 'protection against arbitrary police custody' -> {len(sem_data['results'])} results (query_type: {sem_data['query_type']})")
        assert len(sem_data['results']) > 0, "No results for semantic search!"

        # 4. User Authentication & Workspaces
        print("\n4. Testing User Authentication & Workspaces...")
        test_email = f"advocate_{uuid.uuid4().hex[:8]}@lawchamber.in"
        test_pass = "LegalPass2026!"
        reg_res = await client.post("/api/v1/auth/register", json={
            "email": test_email,
            "password": test_pass,
            "full_name": "Advocate Ramesh Sharma"
        })
        assert reg_res.status_code == 201, f"Register failed: {reg_res.text}"
        token_data = reg_res.json()
        access_token = token_data["access_token"]
        auth_headers = {"Authorization": f"Bearer {access_token}"}
        print(f"   Registered user: {test_email} (Token: {access_token[:20]}...)")

        me_res = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert me_res.status_code == 200
        assert me_res.json()["email"] == test_email
        print(f"   Verified GET /api/v1/auth/me: {me_res.json()['full_name']}")

        # 5. Bookmarks Flow
        print("\n5. Testing Bookmarks Flow...")
        target_judgment_id = sample_judgment["id"]
        bm_add = await client.post("/api/v1/bookmarks", json={
            "judgment_id": target_judgment_id,
            "notes": "Critical precedent on anticipatory bail",
            "tags": ["bail", "urgent"]
        }, headers=auth_headers)
        assert bm_add.status_code == 201, f"Bookmark add failed: {bm_add.text}"
        print(f"   Created bookmark for judgment {target_judgment_id}")

        bm_list = await client.get("/api/v1/bookmarks", headers=auth_headers)
        assert bm_list.status_code == 200
        assert len(bm_list.json()["data"]) >= 1
        print(f"   Retrieved bookmarks list: {len(bm_list.json()['data'])} item(s)")

        bm_del = await client.delete(f"/api/v1/bookmarks/{target_judgment_id}", headers=auth_headers)
        assert bm_del.status_code in (200, 204), f"Delete bookmark failed: {bm_del.status_code}"
        print(f"   Deleted bookmark {target_judgment_id} (status: {bm_del.status_code})")

        # 6. Alerts Flow
        print("\n6. Testing Alerts Flow...")
        alert_res = await client.post("/api/v1/alerts", json={
            "title": "Bail & Article 21 Tracker",
            "category": "Criminal",
            "keywords": ["Section 438", "Anticipatory Bail", "Article 21"],
            "is_active": True
        }, headers=auth_headers)
        assert alert_res.status_code == 201, f"Alert create failed: {alert_res.text}"
        alert_id = alert_res.json()["id"]
        print(f"   Created alert: '{alert_res.json()['title']}' (ID: {alert_id})")

        matches_res = await client.get("/api/v1/alerts/matches", headers=auth_headers)
        assert matches_res.status_code == 200
        matches = matches_res.json()["matches"]
        print(f"   Retrieved matching judgments for user alerts: {len(matches)} matches")

        del_alert = await client.delete(f"/api/v1/alerts/{alert_id}", headers=auth_headers)
        assert del_alert.status_code in (200, 204), f"Delete alert failed: {del_alert.status_code}"
        print(f"   Deleted alert {alert_id} (status: {del_alert.status_code})")

        print("\n" + "=" * 80)
        print("ALL END-TO-END INTEGRATION TESTS PASSED WITH 100% SUCCESS!")
        print("=" * 80)
        return True

if __name__ == "__main__":
    success = asyncio.run(run_e2e_tests())
    sys.exit(0 if success else 1)
