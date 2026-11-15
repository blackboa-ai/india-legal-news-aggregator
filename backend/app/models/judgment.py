"""
Judgment ORM Model
Stores legal judgments, citations, metadata, embeddings, and full-text search vectors.
"""

import uuid
from typing import Any

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TSVECTOR, UUID
from sqlalchemy.orm import relationship

try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    from sqlalchemy.types import UserDefinedType

    class Vector(UserDefinedType):  # type: ignore
        def __init__(self, dim: int = 384):
            self.dim = dim

        def get_col_spec(self, **kw: Any) -> str:
            return f"vector({self.dim})"

from app.core.database import Base


class Judgment(Base):
    """
    SQLAlchemy ORM model for judgments table.
    Includes pgvector 384-dim embedding and PostgreSQL tsvector search column.
    """
    __tablename__ = "judgments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_id = Column(String(128), unique=True, nullable=False, index=True)
    title = Column(Text, nullable=False)
    short_title = Column(String(500), nullable=True)
    court_code = Column(String(50), nullable=False, index=True)
    court_name = Column(String(120), nullable=False)
    court_level = Column(Integer, nullable=False, default=2)  # 1 = SC, 2 = HC, 3 = Tribunal
    judgment_date = Column(Date, nullable=False, index=True)
    subject_category = Column(String(50), nullable=False, index=True)
    excerpt = Column(Text, nullable=False)
    full_text = Column(Text, nullable=True)
    url = Column(Text, nullable=False)
    parties = Column(JSONB, nullable=False, default=list)
    tags = Column(ARRAY(String), nullable=False, default=list)
    source = Column(String(50), nullable=False)  # indiankanoon, livelaw, barandbench, sci
    is_archived = Column(Boolean, default=True)
    classification_confidence = Column(Float, default=0.0)
    embedding = Column(Vector(384), nullable=True)
    search_tsv = Column(TSVECTOR, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    bookmarks = relationship("Bookmark", back_populates="judgment", cascade="all, delete-orphan")
    topic_associations = relationship("TopicJudgment", back_populates="judgment", cascade="all, delete-orphan")
