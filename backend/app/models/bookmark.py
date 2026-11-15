"""
Bookmark ORM Model
Stores user saved judgments.
"""

import uuid
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class Bookmark(Base):
    """
    SQLAlchemy ORM model for user bookmarks.
    Enforces uniqueness per user and judgment.
    """
    __tablename__ = "bookmarks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(100), nullable=False, index=True)
    judgment_id = Column(UUID(as_uuid=True), ForeignKey("judgments.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "judgment_id", name="uq_user_judgment_bookmark"),
    )

    # Relationships
    judgment = relationship("Judgment", back_populates="bookmarks")
