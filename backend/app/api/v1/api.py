"""
API v1 Router Aggregator
India Legal News Aggregator - Free-Tier Architecture (< 250 MB RAM)
Mounts all v1 sub-routers for health, judgments, search, auth, bookmarks, alerts, topics, and admin.
"""

from fastapi import APIRouter

from app.api.v1 import admin, auth, bookmarks, feedback, health, judgments, user

api_router = APIRouter()

# Health router -> /api/v1/health
api_router.include_router(health.router, tags=["Health"])

# Judgments & Search router -> /api/v1/judgments, /api/v1/search, /api/v1/similar, etc.
api_router.include_router(judgments.router, tags=["Judgments & Search"])

# Authentication router -> /api/v1/auth/register, /api/v1/auth/login, /api/v1/auth/google, /api/v1/auth/me
api_router.include_router(auth.router, tags=["Authentication"])

# Bookmarks router -> /api/v1/bookmarks, /api/v1/bookmarks/{id}
api_router.include_router(bookmarks.bookmarks_router, tags=["Bookmarks"])

# Personalized Alerts router -> /api/v1/alerts, /api/v1/alerts/{id}, /api/v1/alerts/matches
api_router.include_router(bookmarks.alerts_router, tags=["Alerts"])

# Research Topics router -> /api/v1/topics, /api/v1/topics/{id}/judgments
api_router.include_router(user.router, tags=["Topics"])

# Feedback & Reviews router -> /api/v1/feedback
api_router.include_router(feedback.router, tags=["Feedback"])

# Admin router -> /api/v1/admin/refresh
api_router.include_router(admin.router, tags=["Admin"])
