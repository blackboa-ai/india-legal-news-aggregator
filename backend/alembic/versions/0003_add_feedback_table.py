"""Add feedbacks table for user reviews and feedback

Revision ID: 0003_add_feedback_table
Revises: 0002_phase3_auth_bookmarks_alerts
Create Date: 2026-11-17

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0003_add_feedback_table"
down_revision: str | None = "0002_phase3_auth_bookmarks_alerts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if "feedbacks" not in tables:
        op.create_table(
            "feedbacks",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
                nullable=False,
            ),
            sa.Column("rating", sa.Integer(), nullable=False),
            sa.Column("feedback_text", sa.Text(), nullable=False),
            sa.Column("email", sa.String(length=255), nullable=True),
            sa.Column("category", sa.String(length=50), server_default="general", nullable=False),
            sa.Column("user_id", sa.String(length=100), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("NOW()"),
                nullable=False,
            ),
        )
        op.create_index("idx_feedbacks_user_id", "feedbacks", ["user_id"])
        op.create_index("idx_feedbacks_rating", "feedbacks", ["rating"])
        op.create_index("idx_feedbacks_category", "feedbacks", ["category"])
        op.create_index("idx_feedbacks_created_at", "feedbacks", ["created_at"])


def downgrade() -> None:
    op.drop_index("idx_feedbacks_created_at", table_name="feedbacks")
    op.drop_index("idx_feedbacks_category", table_name="feedbacks")
    op.drop_index("idx_feedbacks_rating", table_name="feedbacks")
    op.drop_index("idx_feedbacks_user_id", table_name="feedbacks")
    op.drop_table("feedbacks")
