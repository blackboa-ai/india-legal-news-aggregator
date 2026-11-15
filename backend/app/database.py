"""
Database module alias re-exporting Base, engine, AsyncSessionLocal, and get_db.
Maintains compatibility with both app.database and app.core.database imports.
"""

from app.core.database import AsyncSessionLocal, Base, engine, get_db

__all__ = ["AsyncSessionLocal", "Base", "engine", "get_db"]
