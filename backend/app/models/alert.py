"""
Alert ORM Model
India Legal News Aggregator - Free-Tier Architecture (< 250 MB RAM)
Stores user subscriptions to legal domains, courts, keywords, and statutes.
"""

import uuid

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID

from app.core.database import Base


class Alert(Base):
    """
    SQLAlchemy ORM model for user legal topic & statute alerts.
    Enables users to receive personalized feeds/notifications for specific courts,
    subject categories, and statutory sections (e.g., Section 438 CrPC, IBC).
    """
    __tablename__ = "alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    category = Column(String(50), nullable=True, index=True)
    court_code = Column(String(50), nullable=True, index=True)
    keywords = Column(ARRAY(String), nullable=False, default=list)
    query = Column(String(300), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_notified_at = Column(DateTime(timezone=True), nullable=True)
