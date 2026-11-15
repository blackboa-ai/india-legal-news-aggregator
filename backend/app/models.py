"""
Models module alias re-exporting ORM models from app.models package.
Satisfies Phase 0 Master Execution Plan Exit Gate requirements.
"""

from app.models.bookmark import Bookmark
from app.models.judgment import Judgment
from app.models.topic import Topic, TopicJudgment

__all__ = ["Bookmark", "Judgment", "Topic", "TopicJudgment"]
