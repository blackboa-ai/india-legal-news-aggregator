"""
Topic & TopicJudgment ORM Models
Enables custom research folders/topics and linking judgments to topics.
"""

import uuid

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class Topic(Base):
    """
    SQLAlchemy ORM model for user-created research topics/folders.
    """
    __tablename__ = "topics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    judgment_associations = relationship(
        "TopicJudgment",
        back_populates="topic",
        cascade="all, delete-orphan",
    )


class TopicJudgment(Base):
    """
    Join table linking topics and judgments (many-to-many relationship with added_at timestamp).
    """
    __tablename__ = "topic_judgments"

    topic_id = Column(
        UUID(as_uuid=True),
        ForeignKey("topics.id", ondelete="CASCADE"),
        primary_key=True,
    )
    judgment_id = Column(
        UUID(as_uuid=True),
        ForeignKey("judgments.id", ondelete="CASCADE"),
        primary_key=True,
    )
    added_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    topic = relationship("Topic", back_populates="judgment_associations")
    judgment = relationship("Judgment", back_populates="topic_associations")
