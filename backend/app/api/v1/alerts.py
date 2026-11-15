"""
Alerts API Router Alias
India Legal News Aggregator - Free-Tier Architecture (< 250 MB RAM)
Re-exports alerts endpoints from bookmarks module.
"""

from app.api.v1.bookmarks import (
    alerts_router as router,
)
from app.api.v1.bookmarks import (
    create_alert,
    delete_alert,
    get_alert_matches,
    list_alerts,
)

__all__ = [
    "create_alert",
    "delete_alert",
    "get_alert_matches",
    "list_alerts",
    "router",
]
