"""
User ORM Model
India Legal News Aggregator - Free-Tier Architecture (< 250 MB RAM)
Stores user accounts, credentials, and SSO profile identifiers.
"""

import uuid

from sqlalchemy import Boolean, Column, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class User(Base):
    """
    SQLAlchemy ORM model for user accounts.
    Supports email/password authentication and Google OAuth SSO.
    """
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=True)  # Nullable for Google OAuth SSO users
    full_name = Column(String(255), nullable=True)
    google_id = Column(String(255), unique=True, nullable=True, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships to user artifacts by user_id string
    bookmarks = relationship(
        "Bookmark",
        primaryjoin="foreign(Bookmark.user_id) == cast(User.id, String)",
        cascade="all, delete-orphan",
        lazy="select",
    )
    alerts = relationship(
        "Alert",
        primaryjoin="foreign(Alert.user_id) == cast(User.id, String)",
        cascade="all, delete-orphan",
        lazy="select",
    )
