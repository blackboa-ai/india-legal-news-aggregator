"""
Feedback ORM Model
India Legal News Aggregator
Stores user reviews, ratings (1-5), feedback notes, and optional contact information.
"""

import uuid

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class Feedback(Base):
    """
    SQLAlchemy ORM model for user feedback submissions and ratings.
    Supports ratings from 1 to 5, feedback text, optional email, and categorization.
    """
    __tablename__ = "feedbacks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rating = Column(Integer, nullable=False)  # Rating from 1 to 5
    feedback_text = Column(Text, nullable=False)
    email = Column(String(255), nullable=True)
    category = Column(String(50), nullable=False, default="general")
    user_id = Column(String(100), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
